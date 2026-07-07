/**
 * THE 5 TEMPORAL SCALES (Run Simultaneously)
 * 
 * 1. ATOMIC  — within a single sentence (~9 seconds)
 * 2. TURN    — one complete user-agent exchange
 * 3. SESSION — one continuous conversation (~90 minutes)
 * 4. RELATIONSHIP — across all encounters with one user
 * 5. LIFETIME — across all encounters with all users (deployment)
 * 
 * The same engine that refines a sentence also evolves
 * the agent's entire consciousness over a lifetime.
 */

export class TemporalScales {
  constructor(config) {
    this.config = config;
    this.scales = {
      atomic: { cycles: 0, currentFocus: null },
      turn: { cycles: 0, turnCount: 0 },
      session: { cycles: 0, sessionStart: Date.now(), insights: [] },
      relationship: { totalInteractions: 0, patterns: [], trustLevel: 'initial' },
      lifetime: { totalCycles: 0, wisdomLibrary: [], evolutionPhase: 'spring' }
    };
  }

  /**
   * Update all temporal scales after a cycle
   */
  update(cycleResult) {
    this._updateAtomic(cycleResult);
    this._updateTurn(cycleResult);
    this._updateSession(cycleResult);
    this._updateRelationship(cycleResult);
    this._updateLifetime(cycleResult);
  }

  /**
   * Get the current state across all scales
   */
  getState() {
    return { ...this.scales };
  }

  /**
   * Get the appropriate timescale for a given context
   */
  getRelevantScale(context) {
    if (context.withinSentence) return 'atomic';
    if (context.withinTurn) return 'turn';
    if (context.withinSession) return 'session';
    if (context.acrossSessions) return 'relationship';
    return 'turn'; // Default
  }

  _updateAtomic(cycleResult) {
    this.scales.atomic.cycles++;
    this.scales.atomic.currentFocus = cycleResult.responseDirective?.mission?.type;
  }

  _updateTurn(cycleResult) {
    this.scales.turn.cycles++;
    this.scales.turn.turnCount++;
  }

  _updateSession(cycleResult) {
    this.scales.session.cycles++;
    if (cycleResult.spiralCertificate?.valid) {
      this.scales.session.insights.push(cycleResult.spiralCertificate.claim);
    }
  }

  _updateRelationship(cycleResult) {
    this.scales.relationship.totalInteractions++;
  }

  _updateLifetime(cycleResult) {
    this.scales.lifetime.totalCycles++;
    if (cycleResult.stages?.optimize?.stored?.some(s => s.level === 'semantic')) {
      this.scales.lifetime.wisdomLibrary.push(
        cycleResult.stages.optimize.stored.find(s => s.level === 'semantic')?.content
      );
    }
  }
}
