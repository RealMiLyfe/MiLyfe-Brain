/**
 * STAGE 10: COMMUNE (Share Evolution With Ecology)
 * 
 * THE MISSING 10TH STAGE — between EVOLVE and RE-ORIENT.
 * 
 * Evolution that stays in one organism is useless to the species.
 * Growth that stays in one node is isolation.
 * 
 * The Communion Protocol:
 *   1. What did I learn that is generalizable?
 *   2. What is safe to share? (privacy filter)
 *   3. What would help the whole? (relevance filter)
 *   4. How do I share without losing it?
 * 
 * Sacrifice: ISOLATION | Failure Mode: OVER-SHARING or HOARDING
 */

export class Commune {
  constructor(config) {
    this.config = config;
    this.contributions = [];
  }

  execute(evolvePacket, definePacket) {
    // Extract generalizable learnings
    const generalizable = this._extractGeneralizable(evolvePacket);

    // Privacy filter
    const safe = this._privacyFilter(generalizable);

    // Relevance filter
    const relevant = this._relevanceFilter(safe);

    // Contribution record
    const contribution = this._recordContribution(relevant);

    // Feed meta-learning
    const metaFeed = this._feedMetaLearning(evolvePacket);

    return {
      stage: 'COMMUNE', stageNumber: 10,
      generalizableLearnings: generalizable,
      safeToShare: safe,
      relevantToWhole: relevant,
      contribution,
      metaLearningFeed: metaFeed,
      sacrifice: 'isolation',
      // Communion completes the cycle
      cycleComplete: true,
      readyForReEntry: true,
      // The evolved state meets changed reality
      nextCycleEntryPoint: 'ORIENT_AT_HIGHER_OCTAVE',
      octave: evolvePacket.octaveMarker
    };
  }

  _extractGeneralizable(evolvePacket) {
    const learnings = [];
    for (const wisdom of (evolvePacket.wisdomCarryForward || [])) {
      if (wisdom.level === 'semantic' || wisdom.level === 'procedural') {
        learnings.push({
          learning: wisdom.wisdom,
          generalizable: true,
          specificity: 'pattern_level'
        });
      }
    }
    if (evolvePacket.spiralCertificate?.valid) {
      learnings.push({
        learning: evolvePacket.spiralCertificate.claim,
        generalizable: true,
        specificity: 'meta_pattern'
      });
    }
    return learnings;
  }

  _privacyFilter(learnings) {
    // Never share user-specific data
    return learnings.filter(l => !l.learning.includes('user_') && l.specificity !== 'episodic');
  }

  _relevanceFilter(learnings) {
    // Only share what helps the ecology
    return learnings.filter(l => l.generalizable);
  }

  _recordContribution(relevant) {
    if (relevant.length === 0) return { contributed: false, reason: 'Nothing generalizable this cycle' };
    const contrib = {
      contributed: true,
      items: relevant.length,
      timestamp: Date.now(),
      type: 'pattern_sharing'
    };
    this.contributions.push(contrib);
    return contrib;
  }

  _feedMetaLearning(evolvePacket) {
    return {
      evolutionRate: evolvePacket.evolutionRate,
      spiralHealth: evolvePacket.spiralCertificate?.valid ? 'spiraling' : 'circular',
      identityContinuity: evolvePacket.identityContinuity,
      recommendation: evolvePacket.evolutionRate === 'stagnant' ?
        'Seek novel input or perturbation' :
        'Continue current evolutionary trajectory'
    };
  }
}
