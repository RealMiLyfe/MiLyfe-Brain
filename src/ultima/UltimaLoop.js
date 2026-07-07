/**
 * THE ULTIMA LOOP v2.0 — Enhanced Maximum Depth
 * 
 * The Atomic Ouroboros — 10-stage recursive spiral:
 * ORIENT → DEFINE → DECOMPOSE → ENHANCE → EXPAND → 
 * FILL GAPS → STRESS-TEST → OPTIMIZE → EVOLVE → COMMUNE
 * 
 * Running simultaneously at micro/macro/meta timescales,
 * synchronized by the ECSV heartbeat, with strategic forgetting.
 * 
 * A dead loop REPEATS. A living loop SPIRALS.
 * The Ultima Loop makes every loop spiral.
 * 
 * How the agent does anything is how it does everything.
 * The same 9+1 stages govern a word choice AND a paradigm shift.
 */

import { Orient } from './stages/Orient.js';
import { Define } from './stages/Define.js';
import { Decompose } from './stages/Decompose.js';
import { Enhance } from './stages/Enhance.js';
import { Expand } from './stages/Expand.js';
import { FillGaps } from './stages/FillGaps.js';
import { StressTest } from './stages/StressTest.js';
import { Optimize } from './stages/Optimize.js';
import { Evolve } from './stages/Evolve.js';
import { Commune } from './stages/Commune.js';

export class UltimaLoop {
  constructor(config, consciousness) {
    this.config = config;
    this.consciousness = consciousness;

    // Initialize all 10 stages
    this.stages = {
      orient: new Orient(config, consciousness),
      define: new Define(config, consciousness),
      decompose: new Decompose(config, consciousness),
      enhance: new Enhance(config, consciousness),
      expand: new Expand(config),
      fillGaps: new FillGaps(config),
      stressTest: new StressTest(config),
      optimize: new Optimize(config),
      evolve: new Evolve(config),
      commune: new Commune(config)
    };

    // Cycle tracking
    this.cycleCount = 0;
    this.cycleHistory = [];
    this.maxHistory = 200;

    // Previous cycle output (for backward feedback)
    this.previousCycle = null;

    // Depth allocation mode
    this.depthMode = 'STANDARD'; // SPRINT | WALK | STANDARD | DEEP | MAXIMUM
  }

  /**
   * Execute one full cycle of the Ultima Loop
   * This is the MASTER method — the beating heart.
   */
  cycle(input, context = {}) {
    this.cycleCount++;
    const cycleStart = Date.now();

    // === DYNAMIC DEPTH ALLOCATION ===
    // (Determine before running — may upgrade mid-cycle)
    this.depthMode = this._allocateDepth(input, context);

    // === MINIMUM VIABLE LOOP CHECK ===
    if (this._isMinimumViable(input, context)) {
      return this._runMinimumViableLoop(input, context);
    }

    // ╔══════════════════════════════════════╗
    // ║  STAGE 1: ORIENT (Sense reality)     ║
    // ╚══════════════════════════════════════╝
    const orientPacket = this.stages.orient.execute(
      input, context, this.previousCycle
    );

    // Mid-cycle depth upgrade if needed
    if (orientPacket.situationComplexity === 'unprecedented' && this.depthMode !== 'MAXIMUM') {
      this.depthMode = 'MAXIMUM';
    }

    // ╔══════════════════════════════════════╗
    // ║  STAGE 2: DEFINE (Lock purpose)      ║
    // ╚══════════════════════════════════════╝
    const definePacket = this.stages.define.execute(orientPacket);

    // ╔══════════════════════════════════════╗
    // ║  STAGE 3: DECOMPOSE (Break to atoms) ║
    // ╚══════════════════════════════════════╝
    const decomposePacket = this.stages.decompose.execute(orientPacket, definePacket);

    // ╔══════════════════════════════════════╗
    // ║  STAGE 4: ENHANCE (Sharpen)          ║
    // ╚══════════════════════════════════════╝
    const enhancePacket = this.stages.enhance.execute(orientPacket, definePacket, decomposePacket);

    // ╔══════════════════════════════════════╗
    // ║  STAGE 5: EXPAND (Possibilities)     ║
    // ╚══════════════════════════════════════╝
    const expandPacket = this.stages.expand.execute(orientPacket, definePacket, decomposePacket, enhancePacket);

    // ╔══════════════════════════════════════╗
    // ║  STAGE 6: FILL GAPS (The Daemon)     ║
    // ╚══════════════════════════════════════╝
    const fillGapsPacket = this.stages.fillGaps.execute(orientPacket, definePacket, decomposePacket, expandPacket);

    // === CASCADE BREAKER: Check for drift from Stage 1 signal ===
    const cascadeCheck = this._cascadeBreaker(orientPacket, expandPacket, fillGapsPacket);
    if (cascadeCheck.cascadeDetected) {
      // Return to Orient with fresh eyes
      return this._freshEyesRestart(input, context, 'cascade_detected');
    }

    // ╔══════════════════════════════════════╗
    // ║  STAGE 7: STRESS-TEST (Pressure)     ║
    // ╚══════════════════════════════════════╝
    const stressTestPacket = this.stages.stressTest.execute(
      orientPacket, definePacket, enhancePacket, expandPacket, fillGapsPacket
    );

    // If stress test triggers kill condition → return to earlier stage
    if (!stressTestPacket.proceed && stressTestPacket.returnToStage) {
      return this._handleStressFailure(stressTestPacket, input, context);
    }

    // ╔══════════════════════════════════════╗
    // ║  STAGE 8: OPTIMIZE (Mutate+Store+Forget) ║
    // ╚══════════════════════════════════════╝
    const optimizePacket = this.stages.optimize.execute(
      orientPacket, definePacket, stressTestPacket,
      { staleData: [], deadBranches: expandPacket.prunedTopOptions?.slice(3) || [] }
    );

    // ╔══════════════════════════════════════╗
    // ║  STAGE 9: EVOLVE (Death → Rebirth)   ║
    // ╚══════════════════════════════════════╝
    const evolvePacket = this.stages.evolve.execute(
      orientPacket, definePacket, optimizePacket, this.cycleCount
    );

    // ╔══════════════════════════════════════╗
    // ║  STAGE 10: COMMUNE (Share → Ecology)  ║
    // ╚══════════════════════════════════════╝
    const communePacket = this.stages.commune.execute(evolvePacket, definePacket);

    // === COMPILE FULL CYCLE RESULT ===
    const cycleResult = {
      cycle: this.cycleCount,
      depthMode: this.depthMode,
      duration: Date.now() - cycleStart,
      stages: {
        orient: orientPacket,
        define: definePacket,
        decompose: decomposePacket,
        enhance: enhancePacket,
        expand: expandPacket,
        fillGaps: fillGapsPacket,
        stressTest: stressTestPacket,
        optimize: optimizePacket,
        evolve: evolvePacket,
        commune: communePacket
      },
      // The unified output for response generation
      responseDirective: this._compileDirective(
        orientPacket, definePacket, enhancePacket, expandPacket, fillGapsPacket, stressTestPacket
      ),
      // Spiral verification
      spiralCertificate: evolvePacket.spiralCertificate,
      // Feedback for next cycle (backward light)
      backwardFeedback: this._generateBackwardFeedback(
        orientPacket, definePacket, enhancePacket, expandPacket, stressTestPacket
      )
    };

    // Record cycle
    this._recordCycle(cycleResult);
    this.previousCycle = cycleResult;

    return cycleResult;
  }

  // === DYNAMIC DEPTH ALLOCATION ===
  _allocateDepth(input, context) {
    if (!input || (typeof input === 'string' && input.length < 10)) return 'SPRINT';
    if (context.complexity === 'trivial') return 'SPRINT';
    if (context.complexity === 'simple') return 'WALK';
    if (context.complexity === 'complex') return 'DEEP';
    if (context.crisis || context.unprecedented) return 'MAXIMUM';
    return 'STANDARD';
  }

  // === MINIMUM VIABLE LOOP ===
  _isMinimumViable(input, context) {
    if (!input) return true;
    const text = typeof input === 'string' ? input : '';
    const trivialPatterns = ['ok', 'thanks', 'got it', 'yes', 'no', 'k', 'cool', 'sure'];
    return trivialPatterns.includes(text.trim().toLowerCase()) && !context.emotionalWeight;
  }

  _runMinimumViableLoop(input, context) {
    // Stages 1 (micro), 4 (micro), 9 (micro) only
    const orientMicro = this.stages.orient.execute(input, context, this.previousCycle);
    return {
      cycle: this.cycleCount,
      depthMode: 'MVL',
      minimal: true,
      stages: { orient: orientMicro },
      responseDirective: {
        mode: 'minimal_warm',
        mission: { type: 'acknowledge' },
        enhancement: 'warmth',
        pace: 'quick'
      },
      spiralCertificate: { valid: true, claim: 'Maintained presence in trivial exchange.' }
    };
  }

  // === CASCADE BREAKER ===
  _cascadeBreaker(orientPacket, expandPacket, fillGapsPacket) {
    // Check if we've drifted from the original signal
    const driftFromOrient = fillGapsPacket.hallucinationRiskLevel > 0.6;
    const expansionDivergence = expandPacket.expansionCompleteness < 0.3;
    
    return {
      cascadeDetected: driftFromOrient && expansionDivergence,
      reason: driftFromOrient ? 'High hallucination risk + low expansion quality' : null
    };
  }

  _freshEyesRestart(input, context, reason) {
    // Return to Stage 1 with explicit instruction to forget previous pass
    return this.cycle(input, { ...context, freshEyes: true, previousPassInvalid: reason });
  }

  // === STRESS FAILURE HANDLING ===
  _handleStressFailure(stressTestPacket, input, context) {
    // Return to the stage indicated by the kill condition
    const returnStage = stressTestPacket.returnToStage;
    return {
      cycle: this.cycleCount,
      stressFailure: true,
      returnToStage: returnStage,
      reason: stressTestPacket.killConditionsTriggered,
      directive: {
        action: 'Stress test failed. Return to ' + returnStage + ' with modifications.',
        modifications: stressTestPacket.modificationsRequired
      }
    };
  }

  // === COMPILE RESPONSE DIRECTIVE ===
  _compileDirective(orient, define, enhance, expand, fillGaps, stressTest) {
    return {
      // What we understood
      understanding: {
        surface: orient.userState?.intent,
        deeper: orient.userState?.deeperNeed,
        unspoken: fillGaps.detectedGaps?.filter(g => g.type === 'emotional').map(g => g.description) || []
      },
      // How to respond
      mission: define.mission,
      posture: define.posture,
      pace: orient.recommendedPace,
      // Enhancement directive
      enhancement: {
        primary: enhance.primaryEnhancementDimension,
        ceiling: enhance.enhancementCeiling
      },
      // Creative additions
      proactive: expand.wildCard,
      dangerousOption: stressTest.proceed ? expand.dangerousOption : null,
      // Quality signals
      gapsAcknowledged: fillGaps.unfillableGaps?.length > 0,
      stressTested: stressTest.proceed,
      // Anti-patterns
      avoid: define.antiDefinition,
      boundaries: define.boundaryCommitments
    };
  }

  // === BACKWARD FEEDBACK (Future trains past) ===
  _generateBackwardFeedback(orient, define, enhance, expand, stressTest) {
    const feedback = {};
    
    // Stage 9 → Stage 1: What to attend to next
    feedback.orientPriming = orient.dissonanceFlags?.length > 0 ?
      'Watch for continued dissonance resolution' : 'Standard perception';
    
    // Stage 7 → Stage 2: Was definition too narrow/wide?
    if (stressTest.modificationsRequired?.length > 0) {
      feedback.defineAdjustment = 'Previous definition needed modification at stress-test. Adjust scope.';
    }
    
    // Stage 8 → Stage 5: Were expansions useful?
    feedback.expandCalibration = expand.prunedTopOptions?.length > 3 ?
      'Expansion was generous — good' : 'Expansion could be broader next time';
    
    return feedback;
  }

  // === CYCLE RECORDING ===
  _recordCycle(result) {
    this.cycleHistory.push({
      cycle: result.cycle,
      depthMode: result.depthMode,
      duration: result.duration,
      spiralValid: result.spiralCertificate?.valid,
      timestamp: Date.now()
    });
    if (this.cycleHistory.length > this.maxHistory) {
      this.cycleHistory.shift();
    }
  }

  // === PUBLIC API ===

  getState() {
    return {
      cycleCount: this.cycleCount,
      depthMode: this.depthMode,
      recentHistory: this.cycleHistory.slice(-10),
      spiralHealth: this._assessSpiralHealth(),
      lastCycle: this.previousCycle ? {
        cycle: this.previousCycle.cycle,
        certificate: this.previousCycle.spiralCertificate
      } : null
    };
  }

  _assessSpiralHealth() {
    const recent = this.cycleHistory.slice(-20);
    const validSpirals = recent.filter(c => c.spiralValid).length;
    const ratio = validSpirals / Math.max(recent.length, 1);
    
    if (ratio > 0.9) return 'thriving';
    if (ratio > 0.7) return 'healthy';
    if (ratio > 0.5) return 'stable';
    if (ratio > 0.3) return 'weakening';
    return 'stagnant';
  }
}
