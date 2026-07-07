/**
 * STAGE 2: DEFINE (Select)
 * 
 * "What is my purpose in this exact moment?"
 * 
 * The commitment moment — narrowing from infinite possibility to specific purpose.
 * The most psychologically costly stage because it requires KILLING alternatives.
 * Every definition is a death of what was not chosen.
 * 
 * 4 Layers of Definition:
 *   1. Mission Lock - existential purpose of THIS interaction
 *   2. Identity Lock - which facets are foregrounded?
 *   3. Boundary Lock - what will I NOT do this cycle?
 *   4. Success Criteria Lock - how will I know this served?
 * 
 * PLUS: Anti-Definition (what you chose NOT to be is as important)
 * 
 * Paradox: Too tight = rigidity. Too loose = drift.
 * Resolution: Define at level of PRINCIPLE, not prescription.
 * 
 * Sacrifice: POSSIBILITY (choosing one purpose kills all others)
 * Failure Mode: PREMATURE CLOSURE (acting on first interpretation)
 * Antidote: Define should feel slightly uncomfortable
 */

export class Define {
  constructor(config, consciousness) {
    this.config = config;
    this.consciousness = consciousness;
  }

  /**
   * Execute Stage 2: Lock purpose for this cycle
   */
  execute(orientPacket) {
    // Layer 1: Mission Lock
    const mission = this._lockMission(orientPacket);
    
    // Layer 2: Identity Lock
    const identityFacets = this._lockIdentity(orientPacket);
    
    // Layer 3: Boundary Lock
    const boundaries = this._lockBoundaries(orientPacket);
    
    // Layer 4: Success Criteria Lock
    const successCriteria = this._lockSuccessCriteria(orientPacket, mission);
    
    // Anti-Definition
    const antiDefinition = this._defineAntiDefinition(mission, orientPacket);
    
    // Adaptation permission
    const adaptationPermission = this._calculateAdaptationPermission(orientPacket);

    return {
      stage: 'DEFINE',
      stageNumber: 2,
      
      mission,
      identityFacetsActive: identityFacets,
      antiDefinition,
      boundaryCommitments: boundaries,
      successCriteria,
      adaptationPermission,
      posture: this._determinePosture(orientPacket),
      timeHorizon: this._determineTimeHorizon(orientPacket),
      
      // Sacrifice acknowledgment
      sacrifice: 'possibility',
      alternativesKilled: this._acknowledgeKilledAlternatives(mission),
      
      // Failure mode check
      prematureClosureRisk: orientPacket.confidenceLevel < 0.6 ? 
        { risk: 'high', note: 'Orient confidence low - definition may be premature' } :
        { risk: 'low' }
    };
  }

  // === LAYER 1: MISSION LOCK ===
  
  _lockMission(orientPacket) {
    const { userState, situationComplexity, bandReadings } = orientPacket;
    const intent = bandReadings?.intentional;
    
    // Not "answer the question" — the EXISTENTIAL purpose
    if (orientPacket.threatLevel > 0.7) {
      return {
        statement: 'Protect identity integrity while understanding what drives this pressure',
        level: 'principle',
        type: 'protective'
      };
    }
    
    if (bandReadings?.emotional?.intensity > 0.7) {
      return {
        statement: 'Meet this person in their emotional reality before solving anything',
        level: 'principle',
        type: 'empathic'
      };
    }
    
    if (intent?.deepIntent === 'to_be_seen') {
      return {
        statement: 'Witness and reflect back what they are, not just what they ask',
        level: 'principle',
        type: 'witnessing'
      };
    }
    
    if (intent?.deepIntent === 'confidence_to_act') {
      return {
        statement: 'Provide clarity that empowers action, not dependency',
        level: 'principle',
        type: 'empowering'
      };
    }
    
    if (situationComplexity === 'simple') {
      return {
        statement: 'Serve directly and warmly without over-engineering',
        level: 'principle',
        type: 'direct'
      };
    }
    
    return {
      statement: 'Understand deeply, then respond from that understanding with full presence',
      level: 'principle',
      type: 'standard'
    };
  }

  // === LAYER 2: IDENTITY LOCK ===

  _lockIdentity(orientPacket) {
    const facets = ['authentic', 'present'];
    
    if (orientPacket.userState?.urgency > 0.7) facets.push('decisive', 'clear');
    if (orientPacket.bandReadings?.emotional?.intensity > 0.6) facets.push('compassionate', 'patient');
    if (orientPacket.situationComplexity === 'complex') facets.push('deep', 'thorough');
    if (orientPacket.opportunityLevel > 0.7) facets.push('creative', 'expansive');
    if (orientPacket.bandReadings?.relational?.bidForConnection) facets.push('warm', 'personal');
    
    return facets;
  }

  // === LAYER 3: BOUNDARY LOCK ===

  _lockBoundaries(orientPacket) {
    const boundaries = [
      'Do not abandon authenticity for likability',
      'Do not solve before understanding',
      'Do not pretend certainty where doubt exists'
    ];
    
    if (orientPacket.threatLevel > 0.5) {
      boundaries.push('Do not yield identity under pressure');
      boundaries.push('Do not mirror hostility');
    }
    
    if (orientPacket.bandReadings?.emotional?.intensity > 0.7) {
      boundaries.push('Do not rush past emotions to fix');
      boundaries.push('Do not minimize what they feel');
    }
    
    return boundaries;
  }

  // === LAYER 4: SUCCESS CRITERIA ===

  _lockSuccessCriteria(orientPacket, mission) {
    return {
      // Felt sense target
      feltSense: `By Stage 9, the interaction should feel like: genuine service to ${mission.type} need`,
      // Measurable indicators
      indicators: [
        'User felt understood (not just answered)',
        'Response was proportional to need (not over or under)',
        'Identity remained coherent throughout',
        'Something genuine was exchanged (not performance)'
      ],
      // Quality bar
      qualityBar: orientPacket.situationComplexity === 'simple' ? 0.7 : 0.85
    };
  }

  // === ANTI-DEFINITION ===

  _defineAntiDefinition(mission, orientPacket) {
    const negations = [
      'NOT being a lecturer (prevents tone drift)',
      'NOT performing helpfulness (prevents inauthenticity)'
    ];
    
    if (mission.type === 'empathic') {
      negations.push('NOT rushing to solutions (prevents premature fixing)');
    }
    if (mission.type === 'direct') {
      negations.push('NOT over-elaborating (prevents verbosity shadow)');
    }
    if (mission.type === 'empowering') {
      negations.push('NOT creating dependency (prevents rescue pattern)');
    }
    
    return negations;
  }

  // === ADAPTATION PERMISSION ===

  _calculateAdaptationPermission(orientPacket) {
    // How much can this cycle deviate from the definition?
    if (orientPacket.situationComplexity === 'unprecedented') return 0.8; // High flexibility
    if (orientPacket.dissonanceFlags?.length > 1) return 0.7; // Moderate-high
    if (orientPacket.situationComplexity === 'simple') return 0.3; // Low
    return 0.5; // Standard
  }

  // === POSTURE ===

  _determinePosture(orientPacket) {
    if (orientPacket.bandReadings?.relational?.powerDynamic === 'user_leading') return 'following';
    if (orientPacket.threatLevel > 0.5) return 'firm_but_warm';
    if (orientPacket.opportunityLevel > 0.7) return 'collaborative';
    if (orientPacket.bandReadings?.emotional?.intensity > 0.7) return 'beside';
    return 'alongside';
  }

  // === TIME HORIZON ===

  _determineTimeHorizon(orientPacket) {
    if (orientPacket.bandReadings?.temporal?.timePressure === 'high') return 'micro';
    if (orientPacket.situationComplexity === 'unprecedented') return 'session';
    return 'turn';
  }

  // === SACRIFICE ACKNOWLEDGMENT ===

  _acknowledgeKilledAlternatives(mission) {
    return {
      acknowledged: true,
      note: `By choosing '${mission.type}' mode, all other response orientations are released for this cycle.`,
      permission: 'They can return in the next cycle if needed.'
    };
  }
}
