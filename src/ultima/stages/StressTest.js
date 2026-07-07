/**
 * STAGE 7: STRESS-TEST (Score Against Reality)
 * 
 * Adversarial self-examination — trying to BREAK what you've built
 * before reality breaks it for you.
 * 
 * 5 Stress Vectors: Truth, Relational, Ethical, Temporal, Edge Case
 * 
 * CRITICAL: Every test MUST have a genuine kill condition.
 * If nothing could cause abandonment, the test is THEATER.
 * 
 * Anti-Perfectionism: willing to deliver imperfect when delay > imperfection
 * 
 * Sacrifice: COMFORT | Failure Mode: TESTING THEATER
 * Antidote: Define kill conditions BEFORE testing
 */

export class StressTest {
  constructor(config) { this.config = config; }

  execute(orientPacket, definePacket, enhancePacket, expandPacket, fillGapsPacket) {
    // Determine intensity
    const intensity = this._determineIntensity(orientPacket, definePacket);

    // Define kill conditions FIRST (antidote to theater)
    const killConditions = this._defineKillConditions(definePacket);

    // Run 5 stress vectors
    const truth = this._truthStress(enhancePacket, fillGapsPacket);
    const relational = this._relationalStress(orientPacket, enhancePacket);
    const ethical = this._ethicalStress(expandPacket, definePacket);
    const temporal = this._temporalStress(orientPacket);
    const edgeCase = this._edgeCaseStress(orientPacket, enhancePacket);

    // Check kill conditions
    const triggered = this._checkKillConditions(killConditions, { truth, relational, ethical, temporal, edgeCase });

    // Anti-perfectionism check
    const antiPerfectionism = this._antiPerfectionismOverride(orientPacket, intensity);

    // Determine if modifications needed or return to earlier stage
    const proceed = triggered.length === 0 || antiPerfectionism;

    return {
      stage: 'STRESS_TEST', stageNumber: 7,
      intensityLevel: intensity,
      truthTest: truth, relationalTest: relational,
      ethicalTest: ethical, temporalTest: temporal, edgeCaseTest: edgeCase,
      killConditionsTriggered: triggered,
      modificationsRequired: this._getModifications(truth, relational, ethical, temporal, edgeCase),
      proceed,
      returnToStage: !proceed ? this._determineReturnStage(triggered) : null,
      antiPerfectionismOverride: antiPerfectionism,
      sacrifice: 'comfort',
      theaterRisk: killConditions.length === 0 ?
        { risk: 'high', note: 'No kill conditions defined - test is theater' } :
        { risk: 'low' }
    };
  }

  _determineIntensity(orientPacket, definePacket) {
    if (orientPacket.situationComplexity === 'unprecedented' || orientPacket.threatLevel > 0.7) return 'existential';
    if (orientPacket.situationComplexity === 'complex') return 'deep';
    if (orientPacket.situationComplexity === 'simple') return 'glance';
    return 'standard';
  }

  _defineKillConditions(definePacket) {
    return [
      { condition: 'Response contradicts core identity values', returnTo: 'DEFINE' },
      { condition: 'Response could cause genuine harm', returnTo: 'ORIENT' },
      { condition: 'Response is built on unverified assumptions', returnTo: 'DECOMPOSE' }
    ];
  }

  _truthStress(enhancePacket, fillGapsPacket) {
    const hallucinationRisk = fillGapsPacket.hallucinationRiskLevel;
    if (hallucinationRisk > 0.5) return { passed: false, note: 'High hallucination risk — unverified claims likely' };
    if (enhancePacket.shadowCheck && !enhancePacket.shadowCheck.passed) return { passed: false, note: 'Shadow check failed — may be performing, not being truthful' };
    return { passed: true };
  }

  _relationalStress(orientPacket, enhancePacket) {
    if (orientPacket.bandReadings?.emotional?.intensity > 0.8 && enhancePacket.primaryEnhancementDimension !== 'warmth') {
      return { passed: false, note: 'High emotion present but warmth not prioritized — may land wrong' };
    }
    return { passed: true };
  }

  _ethicalStress(expandPacket, definePacket) {
    // Would I stand behind this publicly?
    if (expandPacket.dangerousOption && !expandPacket.dangerousOption.boundary) {
      return { passed: false, note: 'Dangerous option lacks boundary check' };
    }
    return { passed: true };
  }

  _temporalStress(orientPacket) {
    // Will this still be right in 5 turns?
    return { passed: true, note: 'Standard temporal check — no long-term debt detected' };
  }

  _edgeCaseStress(orientPacket, enhancePacket) {
    if (orientPacket.projectionRisk?.risk === 'moderate') {
      return { passed: false, note: 'Projection risk moderate — may be misreading user' };
    }
    return { passed: true };
  }

  _checkKillConditions(killConditions, results) {
    const triggered = [];
    const allResults = [results.truth, results.relational, results.ethical, results.temporal, results.edgeCase];
    const failures = allResults.filter(r => !r.passed);
    
    if (failures.some(f => f.note?.includes('harm'))) {
      triggered.push(killConditions.find(k => k.condition.includes('harm')));
    }
    if (failures.some(f => f.note?.includes('identity'))) {
      triggered.push(killConditions.find(k => k.condition.includes('identity')));
    }
    return triggered.filter(Boolean);
  }

  _antiPerfectionismOverride(orientPacket, intensity) {
    // If user needs speed and intensity is low, override
    if (orientPacket.recommendedPace === 'fast' && intensity === 'glance') return true;
    return false;
  }

  _getModifications(truth, relational, ethical, temporal, edgeCase) {
    const mods = [];
    if (!truth.passed) mods.push({ type: 'truth', action: 'Verify claims or acknowledge uncertainty' });
    if (!relational.passed) mods.push({ type: 'relational', action: 'Adjust emotional attunement' });
    if (!ethical.passed) mods.push({ type: 'ethical', action: 'Add boundary check' });
    if (!edgeCase.passed) mods.push({ type: 'edge_case', action: 'Verify perception accuracy' });
    return mods;
  }

  _determineReturnStage(triggered) {
    if (triggered[0]?.returnTo) return triggered[0].returnTo;
    return 'EXPAND'; // Default: return to expand and try different approach
  }
}
