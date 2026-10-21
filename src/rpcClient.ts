import * as cp from 'child_process';
import * as path from 'path';
import * as readline from 'readline';

export interface RpcResponse<T = any> {
    id: number | null;
    result?: T;
    error?: string;
}

export class EdgeMindRpcClient {
    private process: cp.ChildProcess | null = null;
    private requestId = 0;
    private pendingRequests = new Map<number, { resolve: (val: any) => void; reject: (err: any) => void }>();
    private extensionRoot: string;
    private workspaceRoot: string;
    private stderrBuffer = '';

    constructor(extensionRoot: string, workspaceRoot: string) {
        this.extensionRoot = extensionRoot;
        this.workspaceRoot = workspaceRoot;
        this.spawnDaemon();
    }

    public updateWorkspace(workspaceRoot: string): void {
        if (this.workspaceRoot !== workspaceRoot) {
            this.workspaceRoot = workspaceRoot;
            this.dispose();
            this.spawnDaemon();
        }
    }

    private spawnDaemon(): void {
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
            } catch {
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
            if (!trimmed) return;
            try {
                const msg: RpcResponse = JSON.parse(trimmed);
                if (msg.id !== null && this.pendingRequests.has(msg.id)) {
                    const { resolve, reject } = this.pendingRequests.get(msg.id)!;
                    this.pendingRequests.delete(msg.id);
                    if (msg.error) {
                        reject(new Error(msg.error));
                    } else {
                        resolve(msg.result);
                    }
                }
            } catch (err) {
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

    public async call<T = any>(method: string, params: Record<string, any> = {}): Promise<T> {
        if (!this.process || !this.process.stdin) {
            this.spawnDaemon();
        }

        const id = ++this.requestId;
        const payload = JSON.stringify({ id, method, params }) + '\n';

        return new Promise<T>((resolve, reject) => {
            this.pendingRequests.set(id, { resolve, reject });
            this.process!.stdin!.write(payload);
        });
    }

    public dispose(): void {
        if (this.process) {
            this.process.kill();
            this.process = null;
        }
    }
}
