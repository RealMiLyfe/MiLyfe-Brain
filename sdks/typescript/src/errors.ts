export class MiLyfeBrainError extends Error {
  public statusCode: number;
  public detail: string;

  constructor(statusCode: number, detail: string) {
    super(`HTTP ${statusCode}: ${detail}`);
    this.name = 'MiLyfeBrainError';
    this.statusCode = statusCode;
    this.detail = detail;
  }
}
