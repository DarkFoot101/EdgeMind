"use strict";
var __createBinding = (this && this.__createBinding) || (Object.create ? (function(o, m, k, k2) {
    if (k2 === undefined) k2 = k;
    var desc = Object.getOwnPropertyDescriptor(m, k);
    if (!desc || ("get" in desc ? !m.__esModule : desc.writable || desc.configurable)) {
      desc = { enumerable: true, get: function() { return m[k]; } };
    }
    Object.defineProperty(o, k2, desc);
}) : (function(o, m, k, k2) {
    if (k2 === undefined) k2 = k;
    o[k2] = m[k];
}));
var __setModuleDefault = (this && this.__setModuleDefault) || (Object.create ? (function(o, v) {
    Object.defineProperty(o, "default", { enumerable: true, value: v });
}) : function(o, v) {
    o["default"] = v;
});
var __importStar = (this && this.__importStar) || function (mod) {
    if (mod && mod.__esModule) return mod;
    var result = {};
    if (mod != null) for (var k in mod) if (k !== "default" && Object.prototype.hasOwnProperty.call(mod, k)) __createBinding(result, mod, k);
    __setModuleDefault(result, mod);
    return result;
};
Object.defineProperty(exports, "__esModule", { value: true });
exports.DiffDecorator = void 0;
const vscode = __importStar(require("vscode"));
class DiffDecorator {
    addedDecorationType;
    deletedDecorationType;
    activeHunk = null;
    activeEditor = null;
    _onDidChangeCodeLenses = new vscode.EventEmitter();
    onDidChangeCodeLenses = this._onDidChangeCodeLenses.event;
    constructor() {
        // Solid green background block for added lines
        this.addedDecorationType = vscode.window.createTextEditorDecorationType({
            backgroundColor: 'rgba(46, 160, 67, 0.25)',
            isWholeLine: true,
            overviewRulerColor: '#2ea043',
            overviewRulerLane: vscode.OverviewRulerLane.Right,
        });
        // Solid red background block with strikethrough for deleted lines
        this.deletedDecorationType = vscode.window.createTextEditorDecorationType({
            backgroundColor: 'rgba(248, 81, 73, 0.25)',
            isWholeLine: true,
            textDecoration: 'line-through',
            overviewRulerColor: '#f85149',
            overviewRulerLane: vscode.OverviewRulerLane.Right,
        });
    }
    /**
     * Compute diff segments: prefix, deleted lines (old), added lines (new), suffix.
     */
    computeHunk(originalCode, modifiedCode) {
        const origLines = originalCode.split('\n');
        const modLines = modifiedCode.split('\n');
        let prefixMatch = 0;
        while (prefixMatch < origLines.length &&
            prefixMatch < modLines.length &&
            origLines[prefixMatch] === modLines[prefixMatch]) {
            prefixMatch++;
        }
        let suffixMatch = 0;
        while (suffixMatch < (origLines.length - prefixMatch) &&
            suffixMatch < (modLines.length - prefixMatch) &&
            origLines[origLines.length - 1 - suffixMatch] === modLines[modLines.length - 1 - suffixMatch]) {
            suffixMatch++;
        }
        const prefixLines = origLines.slice(0, prefixMatch);
        const deletedLines = origLines.slice(prefixMatch, origLines.length - suffixMatch);
        const addedLines = modLines.slice(prefixMatch, modLines.length - suffixMatch);
        const suffixLines = origLines.slice(origLines.length - suffixMatch);
        return {
            prefixLines,
            deletedLines,
            addedLines,
            suffixLines,
            originalCode,
            modifiedCode,
            lensLine: Math.max(0, prefixMatch),
        };
    }
    /**
     * Render the visual diff in the active editor with solid RED (old) and GREEN (new) blocks.
     */
    async showPreview(editor, hunk) {
        this.activeEditor = editor;
        this.activeHunk = hunk;
        // Build preview document containing both old code (for red highlight) and new code (for green highlight)
        const previewLines = [
            ...hunk.prefixLines,
            ...hunk.deletedLines,
            ...hunk.addedLines,
            ...hunk.suffixLines,
        ];
        const fullRange = new vscode.Range(editor.document.positionAt(0), editor.document.positionAt(editor.document.getText().length));
        await editor.edit(editBuilder => {
            editBuilder.replace(fullRange, previewLines.join('\n'));
        });
        // 1. Highlight deleted lines with RED background + line-through
        if (hunk.deletedLines.length > 0) {
            const delStart = hunk.prefixLines.length;
            const delEnd = delStart + hunk.deletedLines.length - 1;
            const delRange = new vscode.Range(new vscode.Position(delStart, 0), new vscode.Position(delEnd, 1000));
            editor.setDecorations(this.deletedDecorationType, [delRange]);
        }
        else {
            editor.setDecorations(this.deletedDecorationType, []);
        }
        // 2. Highlight added lines with GREEN background
        if (hunk.addedLines.length > 0) {
            const addStart = hunk.prefixLines.length + hunk.deletedLines.length;
            const addEnd = addStart + hunk.addedLines.length - 1;
            const addRange = new vscode.Range(new vscode.Position(addStart, 0), new vscode.Position(addEnd, 1000));
            editor.setDecorations(this.addedDecorationType, [addRange]);
        }
        else {
            editor.setDecorations(this.addedDecorationType, []);
        }
        this._onDidChangeCodeLenses.fire();
    }
    /**
     * Provide floating CodeLens action buttons: [ ✓ Accept ] and [ ↶ Reject ]
     */
    provideCodeLenses(document) {
        if (!this.activeHunk || !this.activeEditor || document.uri !== this.activeEditor.document.uri) {
            return [];
        }
        const lensPosition = new vscode.Position(this.activeHunk.lensLine, 0);
        const range = new vscode.Range(lensPosition, lensPosition);
        return [
            new vscode.CodeLens(range, {
                title: '✓ Accept (Cmd+Enter)',
                command: 'edgemind.acceptDiff',
                tooltip: 'Accept new code and remove old code',
            }),
            new vscode.CodeLens(range, {
                title: '↶ Reject (Esc)',
                command: 'edgemind.rejectDiff',
                tooltip: 'Discard new code and restore original code',
            }),
        ];
    }
    /**
     * Clear all diff highlights and reset editor state.
     */
    clear(editor) {
        const target = editor || this.activeEditor;
        if (target) {
            target.setDecorations(this.addedDecorationType, []);
            target.setDecorations(this.deletedDecorationType, []);
        }
        this.activeHunk = null;
        this.activeEditor = null;
        this._onDidChangeCodeLenses.fire();
    }
    getActiveHunk() {
        return this.activeHunk;
    }
}
exports.DiffDecorator = DiffDecorator;
//# sourceMappingURL=diffDecorator.js.map