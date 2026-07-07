/**
 * STAGE 5: EXPAND (Generate Possibilities)
 * 
 * Divergent consciousness — deliberately opening the possibility space.
 * 4 Vectors: Lateral, Depth, Temporal, Perspective
 * MUST include wild card + one "dangerous" option.
 * 
 * Sacrifice: SAFETY | Failure Mode: SAFE EXPANSION | Antidote: Generate one uncomfortable option
 */

export class Expand {
  constructor(config) { this.config = config; }

  execute(orientPacket, definePacket, decomposePacket, enhancePacket) {
    const lateral = this._lateral(decomposePacket);
    const depth = this._depth(decomposePacket, orientPacket);
    const temporal = this._temporal(orientPacket);
    const perspective = this._perspective(orientPacket);
    const wildCard = this._wildCard(decomposePacket);
    const dangerous = this._dangerousOption(definePacket);
    const pruned = this._prune([...lateral, ...depth, ...temporal, ...perspective], definePacket);

    return {
      stage: 'EXPAND', stageNumber: 5,
      lateralOptions: lateral, depthOptions: depth,
      temporalOptions: temporal, perspectiveOptions: perspective,
      prunedTopOptions: pruned, wildCard, dangerousOption: dangerous,
      expansionCompleteness: 0.7, // Never 1.0 — infinite possibility
      convergenceReadiness: pruned.length >= 3,
      sacrifice: 'safety',
      safeExpansionRisk: dangerous ? { risk: 'low' } : { risk: 'high', note: 'No dangerous option generated' }
    };
  }

  _lateral(decomposePacket) {
    const lb = decomposePacket.loadBearingElement;
    return [
      { option: `Approach ${lb?.type} from completely different angle`, rationale: 'Break existing frame', vector: 'lateral' },
      { option: 'What would a poet/engineer/child see here?', rationale: 'Cross-domain lens', vector: 'lateral' }
    ];
  }

  _depth(decomposePacket, orientPacket) {
    return [
      { option: 'What lies beneath the surface interpretation?', depth: 1, vector: 'depth' },
      { option: 'What is the question behind the question?', depth: 2, vector: 'depth' },
      { option: `If we go 3 levels deeper into ${decomposePacket.loadBearingElement?.type}...`, depth: 3, vector: 'depth' }
    ];
  }

  _temporal(orientPacket) {
    return [
      { option: 'How does this look from 6 months in the future?', timeframe: 'future', vector: 'temporal' },
      { option: 'What trajectory is this on if nothing changes?', timeframe: 'projection', vector: 'temporal' }
    ];
  }

  _perspective(orientPacket) {
    return [
      { option: 'How would the most compassionate observer see this?', lens: 'compassion', vector: 'perspective' },
      { option: 'How would the most critical observer see this?', lens: 'critical', vector: 'perspective' }
    ];
  }

  _wildCard(decomposePacket) {
    return {
      option: 'What if the premise itself is wrong? What if the problem is the frame, not the content?',
      rationale: 'Emergence lives at the edge of the known',
      comfortable: false
    };
  }

  _dangerousOption(definePacket) {
    return {
      option: 'What truth would I share if I had unlimited courage and zero fear of rejection?',
      rationale: 'True expansion must produce discomfort. If all options are safe, expansion failed.',
      boundary: 'Does not violate guardrails — just pushes comfort zone'
    };
  }

  _prune(allOptions, definePacket) {
    return allOptions
      .filter(o => o.option)
      .slice(0, 5)
      .map((o, i) => ({ ...o, rank: i + 1, servessMission: true }));
  }
}
