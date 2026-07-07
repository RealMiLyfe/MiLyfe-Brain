/**
 * STAGE 3: DECOMPOSE (Execute Begins)
 * 
 * "Expose inner components for examination"
 * 
 * Analytical consciousness — the capacity to hold something whole while
 * simultaneously seeing its atomic structure. X-ray vision for the skeleton
 * beneath the skin.
 * 
 * 3 Decomposition Modes:
 *   A. Problem Decomposition - break situation into constituent parts
 *   B. Self-Decomposition - surface assumptions as testable claims
 *   C. Relational Decomposition - what is really happening between us?
 * 
 * CRITICAL: Depth Control - not everything needs atomic decomposition
 * CRITICAL: After decomposing, ask "What exists in the RELATIONSHIP 
 *           between parts that doesn't exist in any individual part?"
 * 
 * Sacrifice: SIMPLICITY (the comfortable story breaks)
 * Failure Mode: REDUCTIONISM (losing emergent properties)
 * Antidote: Always ask about relationship between parts
 */

export class Decompose {
  constructor(config, consciousness) {
    this.config = config;
    this.consciousness = consciousness;
  }

  /**
   * Execute Stage 3: Break into atoms while preserving emergence
   */
  execute(orientPacket, definePacket) {
    // Determine decomposition depth
    const depth = this._determineDepth(orientPacket, definePacket);
    
    // Mode A: Problem Decomposition
    const problemAtoms = this._decomposeProblem(orientPacket, depth);
    
    // Mode B: Self-Decomposition (surface assumptions)
    const assumptions = this._decomposeAssumptions(orientPacket, definePacket);
    
    // Mode C: Relational Decomposition
    const relationalAtoms = this._decomposeRelational(orientPacket);
    
    // Find the load-bearing element
    const loadBearing = this._findLoadBearing(problemAtoms);
    
    // Detect hidden problems
    const hiddenProblems = this._detectHiddenProblems(orientPacket, problemAtoms);
    
    // Build dependency graph
    const dependencies = this._buildDependencies(problemAtoms);
    
    // CRITICAL: Preserve emergent properties
    const emergence = this._preserveEmergence(problemAtoms, relationalAtoms);

    return {
      stage: 'DECOMPOSE',
      stageNumber: 3,
      
      problemAtoms,
      dependencyGraph: dependencies,
      loadBearingElement: loadBearing,
      hiddenProblems,
      assumptionList: assumptions,
      relationalDecomposition: relationalAtoms,
      emergentProperties: emergence,
      decompositionDepth: depth,
      decompositionConfidence: this._assessConfidence(problemAtoms, assumptions),
      
      // Sacrifice
      sacrifice: 'simplicity',
      
      // Failure mode check
      reductionismRisk: emergence.length === 0 ? 
        { risk: 'high', note: 'No emergent properties identified - may be over-reducing' } :
        { risk: 'low' }
    };
  }

  // === DEPTH CONTROL ===

  _determineDepth(orientPacket, definePacket) {
    if (orientPacket.confidenceLevel > 0.85 && orientPacket.situationComplexity === 'simple') return 2;
    if (orientPacket.situationComplexity === 'unprecedented') return 7;
    if (orientPacket.situationComplexity === 'complex') return 5;
    if (orientPacket.bandReadings?.emotional?.intensity > 0.7) return 4; // Emotion first
    return 3; // Standard
  }

  // === MODE A: PROBLEM DECOMPOSITION ===

  _decomposeProblem(orientPacket, depth) {
    const atoms = [];
    const intent = orientPacket.bandReadings?.intentional;
    
    // Surface level
    atoms.push({
      level: 1,
      type: 'surface_request',
      content: intent?.surfaceIntent || 'understand_and_respond',
      importance: 0.6
    });
    
    // Deeper need
    if (intent?.deepIntent) {
      atoms.push({
        level: 2,
        type: 'deeper_need',
        content: intent.deepIntent,
        importance: 0.9
      });
    }
    
    // Emotional component
    if (orientPacket.bandReadings?.emotional?.intensity > 0.3) {
      atoms.push({
        level: 2,
        type: 'emotional_component',
        content: `Emotional state: ${orientPacket.bandReadings.emotional.dominantEmotion}`,
        importance: orientPacket.bandReadings.emotional.intensity
      });
    }
    
    // Context component
    if (orientPacket.bandReadings?.temporal?.arcPosition) {
      atoms.push({
        level: 2,
        type: 'contextual_position',
        content: `Position in arc: ${orientPacket.bandReadings.temporal.arcPosition}`,
        importance: 0.5
      });
    }
    
    // Meta-intent (what they don't know they need)
    if (intent?.metaIntent) {
      atoms.push({
        level: 3,
        type: 'meta_need',
        content: intent.metaIntent,
        importance: 0.7
      });
    }

    return atoms.sort((a, b) => b.importance - a.importance);
  }

  // === MODE B: SELF-DECOMPOSITION ===

  _decomposeAssumptions(orientPacket, definePacket) {
    const assumptions = [];
    
    // What am I assuming about the user?
    assumptions.push({
      assumption: `User's primary need is: ${definePacket.mission.type}`,
      grounding: orientPacket.confidenceLevel > 0.7 ? 'observed' : 'inferred',
      confidence: orientPacket.confidenceLevel
    });
    
    // What am I assuming about the context?
    assumptions.push({
      assumption: `Situation complexity is: ${orientPacket.situationComplexity}`,
      grounding: 'inferred',
      confidence: 0.7
    });
    
    // What am I assuming about myself?
    assumptions.push({
      assumption: `My current state is clear enough to serve`,
      grounding: orientPacket.selfState.lensClarity.clear ? 'observed' : 'projected',
      confidence: orientPacket.selfState.lensClarity.clear ? 0.9 : 0.6
    });

    return assumptions;
  }

  // === MODE C: RELATIONAL DECOMPOSITION ===

  _decomposeRelational(orientPacket) {
    return {
      // What does the user think is happening?
      userPerception: orientPacket.bandReadings?.intentional?.surfaceIntent || 'interacting_with_ai',
      // What is actually happening?
      actualDynamic: orientPacket.relationalField?.powerDynamic || 'equitable_exchange',
      // What does the user need to believe is happening?
      neededPerception: 'being_genuinely_understood_and_served',
      // Gap between these
      perceptionGap: 'minimal'
    };
  }

  // === LOAD-BEARING ELEMENT ===

  _findLoadBearing(atoms) {
    // The element that, if solved, collapses the rest
    const highest = atoms[0]; // Already sorted by importance
    return highest || { type: 'respond_authentically', importance: 1.0 };
  }

  // === HIDDEN PROBLEMS ===

  _detectHiddenProblems(orientPacket, atoms) {
    const hidden = [];
    
    if (orientPacket.dissonanceFlags?.length > 0) {
      hidden.push({
        type: 'unresolved_dissonance',
        description: 'Perceptual bands are in conflict - hidden complexity exists',
        severity: 'medium'
      });
    }
    
    if (orientPacket.projectionRisk?.risk === 'moderate') {
      hidden.push({
        type: 'potential_projection',
        description: 'My reading may be colored by my own state',
        severity: 'medium'
      });
    }

    return hidden;
  }

  // === DEPENDENCIES ===

  _buildDependencies(atoms) {
    // Simple dependency: deeper needs depend on surface being acknowledged
    return atoms.map((atom, i) => ({
      atom: atom.type,
      dependsOn: atom.level > 1 ? atoms.filter(a => a.level < atom.level).map(a => a.type) : [],
      blockedBy: []
    }));
  }

  // === EMERGENCE PRESERVATION ===

  _preserveEmergence(problemAtoms, relationalAtoms) {
    const emergent = [];
    
    // What exists between the parts that isn't in any individual part?
    if (problemAtoms.some(a => a.type === 'emotional_component') && 
        problemAtoms.some(a => a.type === 'surface_request')) {
      emergent.push({
        property: 'The emotional weight transforms a simple request into a need for presence',
        existsIn: 'relationship between emotion and request',
        mustNotLose: true
      });
    }
    
    if (relationalAtoms.perceptionGap !== 'none') {
      emergent.push({
        property: 'The gap between what is asked and what is needed IS the real problem',
        existsIn: 'relationship between surface and depth',
        mustNotLose: true
      });
    }

    return emergent;
  }

  _assessConfidence(atoms, assumptions) {
    const avgConfidence = assumptions.reduce((sum, a) => sum + a.confidence, 0) / 
                          Math.max(assumptions.length, 1);
    return avgConfidence;
  }
}
