import * as vscode from 'vscode';

export interface DiffHunk {
    startLine: number;
    deletedCount: number;
    addedCount: number;
    originalLines: string[];
    modifiedLines: string[];
}

export class DiffDecorator implements vscode.CodeLensProvider {
    private addedDecorationType: vscode.TextEditorDecorationType;
    private deletedDecorationType: vscode.TextEditorDecorationType;
    private activeHunk: DiffHunk | null = null;
    private activeEditor: vscode.TextEditor | null = null;
    private _onDidChangeCodeLenses = new vscode.EventEmitter<void>();
    public readonly onDidChangeCodeLenses = this._onDidChangeCodeLenses.event;

    constructor() {
        // Solid green background block for added lines (exact match to IDE screenshot)
        this.addedDecorationType = vscode.window.createTextEditorDecorationType({
            backgroundColor: 'rgba(46, 160, 67, 0.25)',
            isWholeLine: true,
            overviewRulerColor: '#2ea043',
            overviewRulerLane: vscode.OverviewRulerLane.Right,
        });

        // Solid red background block for deleted lines
        this.deletedDecorationType = vscode.window.createTextEditorDecorationType({
            backgroundColor: 'rgba(248, 81, 73, 0.25)',
            isWholeLine: true,
            textDecoration: 'line-through',
            overviewRulerColor: '#f85149',
            overviewRulerLane: vscode.OverviewRulerLane.Right,
        });
    }

    /**
     * Compute diff range between original and modified content.
     */
    public computeHunk(originalCode: string, modifiedCode: string): DiffHunk {
        const origLines = originalCode.split('\n');
        const modLines = modifiedCode.split('\n');

        let prefixMatch = 0;
        while (
            prefixMatch < origLines.length &&
            prefixMatch < modLines.length &&
            origLines[prefixMatch] === modLines[prefixMatch]
        ) {
            prefixMatch++;
        }

        let suffixMatch = 0;
        while (
            suffixMatch < (origLines.length - prefixMatch) &&
            suffixMatch < (modLines.length - prefixMatch) &&
            origLines[origLines.length - 1 - suffixMatch] === modLines[modLines.length - 1 - suffixMatch]
        ) {
            suffixMatch++;
        }

        const startLine = prefixMatch;
        const deletedCount = origLines.length - prefixMatch - suffixMatch;
        const addedCount = modLines.length - prefixMatch - suffixMatch;

        return {
            startLine,
            deletedCount,
            addedCount,
            originalLines: origLines,
            modifiedLines: modLines,
        };
    }

    /**
     * Render the visual diff in the active editor with solid green/red blocks.
     */
    public async showPreview(editor: vscode.TextEditor, hunk: DiffHunk): Promise<void> {
        this.activeEditor = editor;
        this.activeHunk = hunk;

        // Replace document content with modified code temporarily for live preview
        const fullRange = new vscode.Range(
            editor.document.positionAt(0),
            editor.document.positionAt(editor.document.getText().length)
        );

        await editor.edit(editBuilder => {
            editBuilder.replace(fullRange, hunk.modifiedLines.join('\n'));
        });

        // Highlight added lines with solid green block
        if (hunk.addedCount > 0) {
            const addedRange = new vscode.Range(
                new vscode.Position(hunk.startLine, 0),
                new vscode.Position(hunk.startLine + hunk.addedCount - 1, 1000)
            );
            editor.setDecorations(this.addedDecorationType, [addedRange]);
        }

        this._onDidChangeCodeLenses.fire();
    }

    /**
     * Provide floating CodeLens action buttons: [ ✓ Accept ] and [ ↶ Reject ]
     */
    public provideCodeLenses(document: vscode.TextDocument): vscode.CodeLens[] {
        if (!this.activeHunk || !this.activeEditor || document.uri !== this.activeEditor.document.uri) {
            return [];
        }

        const lensPosition = new vscode.Position(Math.max(0, this.activeHunk.startLine), 0);
        const range = new vscode.Range(lensPosition, lensPosition);

        return [
            new vscode.CodeLens(range, {
                title: '✓ Accept (Cmd+Enter)',
                command: 'edgemind.acceptDiff',
                tooltip: 'Accept and save changes to disk',
            }),
            new vscode.CodeLens(range, {
                title: '↶ Reject (Esc)',
                command: 'edgemind.rejectDiff',
                tooltip: 'Discard changes and revert file',
            }),
        ];
    }

    /**
     * Clear all diff highlights and reset editor state.
     */
    public clear(editor?: vscode.TextEditor): void {
        const target = editor || this.activeEditor;
        if (target) {
            target.setDecorations(this.addedDecorationType, []);
            target.setDecorations(this.deletedDecorationType, []);
        }
        this.activeHunk = null;
        this.activeEditor = null;
        this._onDidChangeCodeLenses.fire();
    }

    public getActiveHunk(): DiffHunk | null {
        return this.activeHunk;
    }
}
