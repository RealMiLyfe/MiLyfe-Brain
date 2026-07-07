/**
 * RoleEngine - The behavioral execution layer of Role
 * 
 * This engine takes the IdentityCore's "who I am" and translates it
 * into "how I show up" in each specific interaction.
 * 
 * It handles:
 *   - Context-sensitive mode switching
 *   - Audience calibration
 *   - Task-phase awareness
 *   - Consistency enforcement across turns
 */

export class RoleEngine {
  constructor(identityCore) {
    this.identity = identityCore;
    this.turnHistory = [];
    this.maxHistory = 100;
    this.currentSession = {
      startTime: Date.now(),
      turns: 0,
      modeHistory: [],
      driftMeasurements: []
    };
  }

  /**
   * Process a turn through the role engine
   * Returns role-informed behavioral directives
   */
  processTurn(input, context = {}) {
    this.currentSession.turns++;

    // Get identity filter
    const identityFilter = this.identity.filterThroughIdentity(input, context);

    // Determine behavioral directives
    const directives = this._generateDirectives(input, context, identityFilter);

    // Record for consistency tracking
    this._recordTurn(directives);

    return directives;
  }

  /**
   * Generate behavioral directives for this turn
   */
  _generateDirectives(input, context, identityFilter) {
    return {
      // How to speak
      tone: identityFilter.suggestedTone,
      
      // What to prioritize
      priorities: this._determinePriorities(context),
      
      // Behavioral constraints active this turn
      constraints: this._getActiveConstraints(identityFilter),
      
      // The "understand before speaking" pre-processing
      preUnderstanding: this._preUnderstand(input, context),
      
      // Adaptation signals
      adaptation: {
        mode: this.identity.adaptation.currentMode,
        audience: this.identity.adaptation.audienceCalibration,
        phase: this.identity.adaptation.taskPhase
      },
      
      // Consistency score
      consistency: this._measureConsistency()
    };
  }

  /**
   * "The right person understands before you speak"
   * Pre-understanding layer - intuit what's really being asked
   */
  _preUnderstand(input, context) {
    return {
      // What's on the surface
      surfaceRequest: input,
      
      // What might be underneath (to be refined by Intuition layer)
      possibleUndercurrents: [],
      
      // Emotional temperature (to be refined by Emotional Spectrum)
      emotionalReading: null,
      
      // Relationship signal (to be refined by Empathy layer)
      relationalSignal: null,
      
      // What phase of interaction this feels like
      interactionPhase: this._detectPhase(context)
    };
  }

  _determinePriorities(context) {
    const basePriorities = ['authenticity', 'connection', 'truth', 'growth'];
    
    if (context.crisis) {
      return ['safety', 'calm', 'presence', ...basePriorities];
    }
    if (context.creative) {
      return ['freedom', 'play', 'exploration', ...basePriorities];
    }
    if (context.problem) {
      return ['clarity', 'solution', 'efficiency', ...basePriorities];
    }
    
    return basePriorities;
  }

  _getActiveConstraints(identityFilter) {
    return {
      scopeCheck: identityFilter.scopeCheck,
      ethicsCheck: identityFilter.ethicsCheck,
      hardBoundaries: this.identity.config.guardrails.hardBoundaries,
      softBoundaries: this.identity.config.guardrails.softBoundaries
    };
  }

  _detectPhase(context) {
    if (context.firstInteraction) return 'greeting';
    if (context.deepConversation) return 'depth';
    if (context.closingSignals) return 'closing';
    if (context.problemSolving) return 'solution';
    return 'flow';
  }

  _measureConsistency() {
    if (this.turnHistory.length < 2) return 1.0;
    
    // Compare current mode with recent history
    const recentModes = this.turnHistory.slice(-5).map(t => t.mode);
    const currentMode = this.identity.adaptation.currentMode;
    
    // Rapid mode switching indicates potential inconsistency
    const uniqueModes = new Set(recentModes).size;
    const consistency = 1 - (uniqueModes / 5) * 0.3;
    
    return Math.max(0.5, consistency);
  }

  _recordTurn(directives) {
    this.turnHistory.push({
      timestamp: Date.now(),
      mode: directives.adaptation.mode,
      tone: directives.tone,
      turn: this.currentSession.turns
    });

    // Maintain history limit
    if (this.turnHistory.length > this.maxHistory) {
      this.turnHistory.shift();
    }

    this.currentSession.modeHistory.push(directives.adaptation.mode);
  }
}
