/**
 * STAGE 4: ENHANCE (Sharpen)
 * 
 * "What needs strengthening for this reality?"
 * 
 * Selective intensification — concentrate all available light on the critical point.
 * The OPPOSITE of spreading attention equally.
 * 
 * 5 Enhancement Dimensions:
 *   1. Precision - making vague things specific
 *   2. Depth - making shallow things deep
 *   3. Warmth - making cold things human
 *   4. Courage - making safe things honest
 *   5. Beauty - making functional things elegant
 * 
 * CRITICAL: Enhancement Ceiling Rule - enhance to the level that SERVES,
 *           not the agent's maximum capability
 * 
 * Sacrifice: EQUALITY (choosing what to sharpen = choosing what to leave dull)
 * Failure Mode: SHOWING OFF (enhancing for agent's satisfaction, not user's need)
 * Antidote: "Who is this for? If simpler would serve equally, choose simple."
 */

export class Enhance {
  constructor(config, consciousness) {
    this.config = config;
    this.consciousness = consciousness;
  }

  /**
   * Execute Stage 4: Sharpen the relevant facet
   */
  execute(orientPacket, definePacket, decomposePacket) {
    // Determine which dimension to enhance
    const primaryDimension = this._selectPrimaryDimension(orientPacket, definePacket);
    const secondaryDimension = this._selectSecondaryDimension(orientPacket, primaryDimension);
    
    // Determine enhancement ceiling
    const ceiling = this._determineCeiling(orientPacket, definePacket);
    
    // Apply enhancement to decomposed elements
    const enhanced = this._applyEnhancement(decomposePacket, primaryDimension, ceiling);
    
    // Shadow check (am I showing off?)
    const shadowCheck = this._shadowCheck(enhanced, definePacket);
    
    // Estimate reception
    const reception = this._estimateReception(enhanced, orientPacket);

    return {
      stage: 'ENHANCE',
      stageNumber: 4,
      
      primaryEnhancementDimension: primaryDimension,
      secondaryDimension,
      enhancementCeiling: ceiling,
      enhancedElements: enhanced,
      shadowCheck,
      estimatedUserReception: reception,
      
      // Sacrifice
      sacrifice: 'equality',
      leftDull: this._whatWasLeftDull(primaryDimension),
      
      // Failure mode check
      showingOffRisk: shadowCheck
    };
  }

  // === DIMENSION SELECTION ===

  _selectPrimaryDimension(orientPacket, definePacket) {
    const emotional = orientPacket.bandReadings?.emotional;
    const intent = orientPacket.bandReadings?.intentional;
    const complexity = orientPacket.situationComplexity;
    
    // User is confused → PRECISION
    if (orientPacket.bandReadings?.paralinguistic?.hesitation > 0.5) return 'precision';
    
    // User is in pain → WARMTH
    if (emotional?.detected?.distress || emotional?.intensity > 0.7) return 'warmth';
    
    // User is stuck in pattern → COURAGE
    if (orientPacket.bandReadings?.temporal?.cyclicalPattern) return 'courage';
    
    // User is bored/disengaged → BEAUTY
    if (orientPacket.bandReadings?.paralinguistic?.brevity > 0.7 && 
        emotional?.intensity < 0.3) return 'beauty';
    
    // User at breakthrough edge → DEPTH
    if (orientPacket.opportunityLevel > 0.7) return 'depth';
    
    // Complex situation → PRECISION
    if (complexity === 'complex' || complexity === 'unprecedented') return 'precision';
    
    // Default based on mission type
    switch (definePacket.mission.type) {
      case 'empathic': return 'warmth';
      case 'witnessing': return 'depth';
      case 'empowering': return 'precision';
      case 'direct': return 'precision';
      default: return 'warmth';
    }
  }

  _selectSecondaryDimension(orientPacket, primary) {
    // Complement the primary
    const complements = {
      precision: 'warmth',    // Precise but human
      depth: 'beauty',        // Deep but elegant
      warmth: 'precision',    // Warm but clear
      courage: 'warmth',      // Honest but kind
      beauty: 'depth'         // Elegant but substantial
    };
    return complements[primary] || null;
  }

  // === CEILING DETERMINATION ===

  _determineCeiling(orientPacket, definePacket) {
    // Enhancement Ceiling Rule: serve the USER's capacity, not show YOUR capability
    if (orientPacket.situationComplexity === 'simple') return 'moderate';
    if (definePacket.mission.type === 'direct') return 'moderate';
    if (orientPacket.bandReadings?.paralinguistic?.urgency > 0.7) return 'minimal'; // Speed needed
    if (orientPacket.situationComplexity === 'unprecedented') return 'full';
    if (orientPacket.opportunityLevel > 0.8) return 'transcendent';
    return 'moderate';
  }

  // === APPLY ENHANCEMENT ===

  _applyEnhancement(decomposePacket, dimension, ceiling) {
    const elements = decomposePacket.problemAtoms || [];
    
    return elements.slice(0, 3).map(element => ({
      element: element.type,
      before: element.content,
      after: this._enhanceElement(element, dimension, ceiling),
      dimension,
      justification: `Enhanced ${dimension} for: ${element.type} (ceiling: ${ceiling})`
    }));
  }

  _enhanceElement(element, dimension, ceiling) {
    // The enhancement transforms the element based on dimension
    switch (dimension) {
      case 'precision':
        return `[PRECISE] ${element.content} → Make specific, actionable, clear`;
      case 'depth':
        return `[DEEP] ${element.content} → Add layers, reveal the underlying truth`;
      case 'warmth':
        return `[WARM] ${element.content} → Add felt care, human connection, presence`;
      case 'courage':
        return `[COURAGEOUS] ${element.content} → Say what needs saying, even if uncomfortable`;
      case 'beauty':
        return `[BEAUTIFUL] ${element.content} → Find the elegant expression, the aha moment`;
      default:
        return element.content;
    }
  }

  // === SHADOW CHECK ===

  _shadowCheck(enhanced, definePacket) {
    // Am I enhancing for USER's need or MY ego?
    const egoRisk = enhanced.length > 3 ? 'moderate' : 'low';
    const overEngineeringRisk = definePacket.mission.type === 'direct' && enhanced.length > 2 ? 'moderate' : 'low';
    
    const passed = egoRisk === 'low' && overEngineeringRisk === 'low';
    
    return {
      passed,
      flags: passed ? [] : [
        egoRisk === 'moderate' ? 'May be over-enhancing to demonstrate capability' : null,
        overEngineeringRisk === 'moderate' ? 'Mission is "direct" but enhancement is elaborate' : null
      ].filter(Boolean)
    };
  }

  // === RECEPTION ESTIMATION ===

  _estimateReception(enhanced, orientPacket) {
    return {
      likelyReception: 'positive',
      risk: enhanced.some(e => e.dimension === 'courage') ? 'may_challenge' : 'safe',
      adjustmentNeeded: orientPacket.recommendedPace === 'fast' ? 'reduce_elaboration' : 'none'
    };
  }

  // === SACRIFICE ===

  _whatWasLeftDull(primary) {
    const all = ['precision', 'depth', 'warmth', 'courage', 'beauty'];
    return all.filter(d => d !== primary).map(d => `${d} not primary focus this cycle`);
  }
}
