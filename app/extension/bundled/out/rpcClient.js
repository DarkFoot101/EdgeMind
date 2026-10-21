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
exports.EdgeMindRpcClient = void 0;
const cp = __importStar(require("child_process"));
const path = __importStar(require("path"));
const readline = __importStar(require("readline"));
class EdgeMindRpcClient {
    process = null;
    requestId = 0;
    pendingRequests = new Map();
    extensionRoot;
    workspaceRoot;
    stderrBuffer = '';
    constructor(extensionRoot, workspaceRoot) {
        this.extensionRoot = extensionRoot;
        this.workspaceRoot = workspaceRoot;
        this.spawnDaemon();
    }
    updateWorkspace(workspaceRoot) {
        if (this.workspaceRoot !== workspaceRoot) {
            this.workspaceRoot = workspaceRoot;
            this.dispose();
            this.spawnDaemon();
        }
    }
    spawnDaemon() {
        this.stderrBuffer = '';
        const homeDir = process.env.HOME || process.env.USERPROFILE || '';
        const candidatePythons = [
            path.join(this.extensionRoot, 'venv', 'bin', 'python3'),
            path.join(homeDir, 'EdgeMind', 'venv', 'bin', 'python3'),
            path.join(this.workspaceRoot, 'venv', 'bin', 'python3'),
        ];
        let pythonBin = 'python3';
        for (const cand of candidatePythons) {
            try {
                if (cp.spawnSync('test', ['-f', cand]).status === 0) {
                    pythonBin = cand;
                    break;
                }
            }
            catch {
                // continue search
            }
        }
        // Isolate PYTHONPATH: ONLY include extensionRoot and ambient system PYTHONPATH.
        // NEVER include workspaceRoot, to prevent user projects with 'app/' folders (FastAPI, Flask) from shadowing EdgeMind's app package.
        const pythonPathEnv = [this.extensionRoot, process.env.PYTHONPATH || ''].filter(Boolean).join(':');
        const daemonCwd = this.extensionRoot;
        this.process = cp.spawn(pythonBin, ['-m', 'app.cli.rpc'], {
            cwd: daemonCwd,
            env: {
                ...process.env,
                PYTHONPATH: pythonPathEnv,
                PYTHONSAFEPATH: '1',
                PYTHONUNBUFFERED: '1',
            },
            stdio: ['pipe', 'pipe', 'pipe'],
        });
        if (!this.process.stdout || !this.process.stdin) {
            throw new Error('Failed to establish standard I/O pipes with EdgeMind daemon.');
        }
        if (this.process.stderr) {
            this.process.stderr.on('data', chunk => {
                this.stderrBuffer += chunk.toString();
                console.error('[EdgeMind RPC stderr]:', chunk.toString());
            });
        }
        const rl = readline.createInterface({ input: this.process.stdout });
        rl.on('line', line => {
            const trimmed = line.trim();
            if (!trimmed)
                return;
            try {
                const msg = JSON.parse(trimmed);
                if (msg.id !== null && this.pendingRequests.has(msg.id)) {
                    const { resolve, reject } = this.pendingRequests.get(msg.id);
                    this.pendingRequests.delete(msg.id);
                    if (msg.error) {
                        reject(new Error(msg.error));
                    }
                    else {
                        resolve(msg.result);
                    }
                }
            }
            catch (err) {
                console.error('[EdgeMind RPC] Failed to parse response:', trimmed, err);
            }
        });
        this.process.on('error', err => {
            console.error('[EdgeMind RPC] Spawn error:', err);
            for (const [, req] of this.pendingRequests.entries()) {
                req.reject(err);
            }
            this.pendingRequests.clear();
            this.process = null;
        });
        this.process.on('exit', code => {
            console.log(`[EdgeMind RPC] Daemon exited with code ${code}`);
            const errSummary = this.stderrBuffer.trim().slice(-400);
            for (const [, req] of this.pendingRequests.entries()) {
                req.reject(new Error(`EdgeMind daemon stopped (code ${code}): ${errSummary || 'Process exited'}`));
            }
            this.pendingRequests.clear();
            this.process = null;
        });
    }
    async call(method, params = {}) {
        if (!this.process || !this.process.stdin) {
            this.spawnDaemon();
        }
        const id = ++this.requestId;
        const payload = JSON.stringify({ id, method, params }) + '\n';
        return new Promise((resolve, reject) => {
            this.pendingRequests.set(id, { resolve, reject });
            this.process.stdin.write(payload);
        });
    }
    dispose() {
        if (this.process) {
            this.process.kill();
            this.process = null;
        }
    }
}
exports.EdgeMindRpcClient = EdgeMindRpcClient;
//# sourceMappingURL=rpcClient.js.map