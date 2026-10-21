import * as vscode from 'vscode';
import { DiffDecorator } from './diffDecorator';
import { EdgeMindRpcClient } from './rpcClient';

let rpcClient: EdgeMindRpcClient | null = null;
let originalCodeSnapshot = '';
let targetFilePath = '';
let targetSourceHash: string | undefined = undefined;

export function activate(context: vscode.ExtensionContext) {
    const extensionRoot = context.extensionPath;
    const getWorkspaceRoot = () => vscode.workspace.workspaceFolders?.[0]?.uri.fsPath || process.cwd();
    let workspaceRoot = getWorkspaceRoot();

    rpcClient = new EdgeMindRpcClient(extensionRoot, workspaceRoot);
    const diffDecorator = new DiffDecorator();

    vscode.workspace.onDidChangeWorkspaceFolders(() => {
        workspaceRoot = getWorkspaceRoot();
        rpcClient?.updateWorkspace(workspaceRoot);
    });

    // Register CodeLens provider for floating [✓ Accept] [↶ Reject] buttons
    context.subscriptions.push(
        vscode.languages.registerCodeLensProvider({ scheme: 'file' }, diffDecorator)
    );

    // Status bar item
    const statusBarItem = vscode.window.createStatusBarItem(vscode.StatusBarAlignment.Right, 100);
    statusBarItem.text = '$(sparkle) EdgeMind';
    statusBarItem.tooltip = 'EdgeMind Local AI Coding Assistant';
    statusBarItem.command = 'edgemind.showStatus';
    statusBarItem.show();
    context.subscriptions.push(statusBarItem);

    // Command 1: Inline AI Edit (Cmd+I)
    const inlineEditCmd = vscode.commands.registerCommand('edgemind.inlineEdit', async () => {
        const editor = vscode.window.activeTextEditor;
        if (!editor) {
            vscode.window.showInformationMessage('EdgeMind: Please open a code file first.');
            return;
        }

        const instruction = await vscode.window.showInputBox({
            prompt: 'EdgeMind: Describe the change you want to make',
            placeHolder: 'e.g. Convert function to class, or add type annotations',
        });

        if (!instruction) {
            return;
        }

        targetFilePath = editor.document.uri.fsPath;
        originalCodeSnapshot = editor.document.getText();
        const fileProjectRoot = vscode.workspace.getWorkspaceFolder(editor.document.uri)?.uri.fsPath || workspaceRoot;
        rpcClient?.updateWorkspace(fileProjectRoot);

        // Check if user selected a specific text block
        const selection = editor.selection;
        let startLine: number | undefined = undefined;
        let endLine: number | undefined = undefined;
        if (!selection.isEmpty) {
            startLine = selection.start.line + 1;
            endLine = selection.end.line + 1;
        }

        vscode.window.withProgress(
            {
                location: vscode.ProgressLocation.Notification,
                title: startLine ? `EdgeMind: Modifying lines ${startLine}-${endLine}...` : 'EdgeMind: Generating AST verified edit...',
                cancellable: true,
            },
            async (_progress, token) => {
                try {
                    let isCancelled = false;
                    token.onCancellationRequested(() => {
                        isCancelled = true;
                    });

                    const result = await rpcClient!.call('prepare_edit', {
                        file_path: targetFilePath,
                        instruction,
                        project_path: fileProjectRoot,
                        start_line: startLine,
                        end_line: endLine,
                    });

                    if (isCancelled) {
                        return;
                    }

                    if (!result.success) {
                        vscode.window.showErrorMessage(`EdgeMind Edit Failed: ${result.error || result.validation_message}`);
                        return;
                    }

                    targetSourceHash = result.source_hash;
                    const hunk = diffDecorator.computeHunk(originalCodeSnapshot, result.modified_code);
                    await diffDecorator.showPreview(editor, hunk);

                    vscode.window.showInformationMessage(
                        `EdgeMind: Generated preview (${result.metrics?.inference_time_seconds || 0}s). Click Accept or Reject.`,
                        'Accept',
                        'Reject'
                    ).then(selection => {
                        if (selection === 'Accept') {
                            vscode.commands.executeCommand('edgemind.acceptDiff');
                        } else if (selection === 'Reject') {
                            vscode.commands.executeCommand('edgemind.rejectDiff');
                        }
                    });
                } catch (err: any) {
                    vscode.window.showErrorMessage(`EdgeMind RPC Error: ${err.message}`);
                }
            }
        );
    });

    // Command 2: Accept Diff (Cmd+Enter)
    const acceptDiffCmd = vscode.commands.registerCommand('edgemind.acceptDiff', async () => {
        const editor = vscode.window.activeTextEditor;
        const hunk = diffDecorator.getActiveHunk();
        if (!hunk || !editor) {
            return;
        }

        try {
            await editor.document.save();
            await rpcClient!.call('apply_edit', {
                file_path: targetFilePath,
                modified_code: editor.document.getText(),
                source_hash: targetSourceHash,
                project_path: workspaceRoot,
                force: true,
            });

            diffDecorator.clear(editor);
            vscode.window.showInformationMessage('✓ EdgeMind: Changes accepted and saved to disk.');
        } catch (err: any) {
            vscode.window.showErrorMessage(`Failed to save edit: ${err.message}`);
        }
    });

    // Command 3: Reject Diff (Esc)
    const rejectDiffCmd = vscode.commands.registerCommand('edgemind.rejectDiff', async () => {
        const editor = vscode.window.activeTextEditor;
        if (!editor || !originalCodeSnapshot) {
            diffDecorator.clear();
            return;
        }

        // Revert document to original snapshot
        const fullRange = new vscode.Range(
            editor.document.positionAt(0),
            editor.document.positionAt(editor.document.getText().length)
        );

        await editor.edit(editBuilder => {
            editBuilder.replace(fullRange, originalCodeSnapshot);
        });

        diffDecorator.clear(editor);
        vscode.window.showInformationMessage('✗ EdgeMind: Changes rejected. File was left untouched.');
    });

    // Command 4: Show Status
    const statusCmd = vscode.commands.registerCommand('edgemind.showStatus', async () => {
        try {
            const status = await rpcClient!.call('ping');
            vscode.window.showInformationMessage(`EdgeMind Status: ${status.message || 'Connected'}`);
        } catch (err: any) {
            vscode.window.showErrorMessage(`EdgeMind Status: Not responding (${err.message})`);
        }
    });

    context.subscriptions.push(inlineEditCmd, acceptDiffCmd, rejectDiffCmd, statusCmd);
}

export function deactivate() {
    if (rpcClient) {
        rpcClient.dispose();
        rpcClient = null;
    }
}
