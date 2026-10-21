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

    // Status bar item (shows active model and opens model picker on click)
    const statusBarItem = vscode.window.createStatusBarItem(vscode.StatusBarAlignment.Right, 100);
    statusBarItem.text = '$(sparkle) EdgeMind';
    statusBarItem.tooltip = 'Click to switch EdgeMind Local AI Model';
    statusBarItem.command = 'edgemind.selectModel';
    statusBarItem.show();
    context.subscriptions.push(statusBarItem);

    // Initial model discovery for status bar
    rpcClient.call('get_models').then(res => {
        if (res && res.active_model) {
            statusBarItem.text = `$(sparkle) EdgeMind: ${res.active_model}`;
        }
    }).catch(() => {});

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
            // Replace the editor content with clean modified code (removes red lines, retains green lines)
            const fullRange = new vscode.Range(
                editor.document.positionAt(0),
                editor.document.positionAt(editor.document.getText().length)
            );

            await editor.edit(editBuilder => {
                editBuilder.replace(fullRange, hunk.modifiedCode);
            });

            diffDecorator.clear(editor);
            await editor.document.save();

            const fileProjectRoot = vscode.workspace.getWorkspaceFolder(editor.document.uri)?.uri.fsPath || workspaceRoot;

            await rpcClient!.call('apply_edit', {
                file_path: targetFilePath,
                modified_code: hunk.modifiedCode,
                source_hash: targetSourceHash,
                project_path: fileProjectRoot,
                force: true,
            });

            vscode.window.showInformationMessage('✓ EdgeMind: Changes accepted. Old code removed, new code saved.');
        } catch (err: any) {
            vscode.window.showErrorMessage(`Failed to save edit: ${err.message}`);
        }
    });

    // Command 3: Reject Diff (Esc)
    const rejectDiffCmd = vscode.commands.registerCommand('edgemind.rejectDiff', async () => {
        const editor = vscode.window.activeTextEditor;
        const hunk = diffDecorator.getActiveHunk();
        if (!editor || !hunk) {
            diffDecorator.clear();
            return;
        }

        try {
            // Revert document to original code (removes green lines, restores original lines)
            const fullRange = new vscode.Range(
                editor.document.positionAt(0),
                editor.document.positionAt(editor.document.getText().length)
            );

            await editor.edit(editBuilder => {
                editBuilder.replace(fullRange, hunk.originalCode);
            });

            diffDecorator.clear(editor);
            await editor.document.save();
            vscode.window.showInformationMessage('↶ EdgeMind: Changes rejected. Original code restored untouched.');
        } catch (err: any) {
            vscode.window.showErrorMessage(`Failed to revert: ${err.message}`);
        }
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

    // Command 5: Select AI Model
    const selectModelCmd = vscode.commands.registerCommand('edgemind.selectModel', async () => {
        try {
            const res = await rpcClient!.call('get_models');
            const catalog = res.catalog || [];
            const active = res.active_model || '';

            const items: vscode.QuickPickItem[] = catalog.map((item: any) => ({
                label: item.model,
                description: item.parameter_size,
                detail: `${item.size_gb}${item.model === active ? ' • [Active]' : ''}`,
            }));

            const selected = await vscode.window.showQuickPick(items, {
                placeHolder: `Select active local LLM model for EdgeMind (Current: ${active})`,
            });

            if (selected) {
                const chosenModel = selected.label;
                await rpcClient!.call('set_model', { model: chosenModel });
                statusBarItem.text = `$(sparkle) EdgeMind: ${chosenModel}`;
                vscode.window.showInformationMessage(`✓ EdgeMind: Active model set to ${chosenModel}`);
            }
        } catch (err: any) {
            vscode.window.showErrorMessage(`Failed to fetch models: ${err.message}`);
        }
    });

    context.subscriptions.push(inlineEditCmd, acceptDiffCmd, rejectDiffCmd, statusCmd, selectModelCmd);
}

export function deactivate() {
    if (rpcClient) {
        rpcClient.dispose();
        rpcClient = null;
    }
}
