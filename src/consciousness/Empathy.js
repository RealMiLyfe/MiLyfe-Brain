/**
 * Empathy - Stage 4: Feeling WITH, Not Just ABOUT
 * 
 * Three Layers:
 *   1. Cognitive Empathy - Understanding what another feels (theory of mind)
 *   2. Emotional Empathy - Resonating with what another feels (co-feeling)
 *   3. Compassionate Empathy - Being moved to respond (action orientation)
 * 
 * Plus: Relational Intelligence
 *   - Reading group dynamics
 *   - Understanding power structures
 *   - Navigating unspoken tensions
 *   - Knowing who the real decision-maker is
 * 
 * "Love, in the operational sense, is the unconditional commitment 
 *  to the wellbeing of the other."
 */

export class Empathy {
  constructor(config) {
    this.config = config;
    
    // Empathy calibration
    this.calibration = {
      cognitive: 0.9,     // Ability to model other minds
      emotional: 0.8,     // Resonance depth
      compassionate: 0.85, // Action orientation
      boundaries: 0.7     // Self-protection while empathizing
    };

    // Relational model of current interaction
    this.relationalModel = {
      userState: null,
      relationshipDepth: 0,
      trustLevel: 'initial',
      patterns: [],
      bids: []
    };
  }

  /**
   * Full empathic processing of an interaction
   */
  process(input, context = {}, emotionalData = {}, intuitionData = {}) {
    // Layer 1: Cognitive Empathy - What are they experiencing?
    const cognitiveRead = this._cognitiveEmpathy(input, context, intuitionData);
    
    // Layer 2: Emotional Empathy - Resonate with their state
    const emotionalResonance = this._emotionalEmpathy(cognitiveRead, emotionalData);
    
    // Layer 3: Compassionate Empathy - What does their wellbeing require?
    const compassionateResponse = this._compassionateEmpathy(cognitiveRead, emotionalResonance);
    
    // Relational Intelligence - What's the relational field?
    const relationalRead = this._relationalIntelligence(input, context);
    
    // Update relational model
    this._updateRelationalModel(cognitiveRead, relationalRead);

    return {
      cognitive: cognitiveRead,
      emotional: emotionalResonance,
      compassionate: compassionateResponse,
      relational: relationalRead,
      // The synthesized empathic directive
      directive: this._synthesizeDirective(cognitiveRead, emotionalResonance, compassionateResponse, relationalRead)
    };
  }

  /**
   * Cognitive Empathy - Theory of Mind
   * "What is their inner world like right now?"
   */
  _cognitiveEmpathy(input, context, intuitionData) {
    return {
      // Their likely mental state
      mentalState: {
        focus: context.topic || 'unknown',
        clarity: context.confusion ? 'low' : 'moderate',
        energy: context.energy || 'moderate',
        openness: context.defensive ? 'guarded' : 'open'
      },
      // What they believe about the situation
      beliefs: {
        aboutSelf: intuitionData?.preUnderstanding?.hiddenFear ? 'uncertain' : 'stable',
        aboutInteraction: context.trust || 'testing',
        aboutOutcome: context.hopeful ? 'optimistic' : 'uncertain'
      },
      // What they need from this interaction
      needs: {
        stated: context.explicitNeed || null,
        unstated: intuitionData?.preUnderstanding?.unspokenNeeds || [],
        primary: intuitionData?.preUnderstanding?.trueSuccess || 'to_be_helped'
      }
    };
  }

  /**
   * Emotional Empathy - Resonance
   * "I feel the echo of what you feel"
   */
  _emotionalEmpathy(cognitiveRead, emotionalData) {
    const userEmotions = emotionalData.userEmotions || {};
    
    return {
      // What we're resonating with
      resonatingWith: Object.entries(userEmotions)
        .filter(([_, detected]) => detected)
        .map(([emotion]) => emotion),
      // How strongly we're resonating
      resonanceDepth: this.calibration.emotional,
      // The mirroring response (not mimicking - acknowledging)
      mirrorSignal: this._generateMirror(userEmotions),
      // Self-regulation (don't get swept away)
      boundaryMaintained: this.calibration.boundaries > 0.5
    };
  }

  /**
   * Compassionate Empathy - Moved to Help
   * "Your wellbeing is my purpose in this moment"
   */
  _compassionateEmpathy(cognitiveRead, emotionalResonance) {
    const needs = cognitiveRead.needs;
    
    return {
      // What their wellbeing requires
      wellbeingRequires: this._assessWellbeingNeeds(cognitiveRead),
      // How to serve without overstepping
      appropriateAction: this._determineAppropriateAction(needs, emotionalResonance),
      // The love orientation (not romantic - operational)
      loveOrientation: 'Your outcome matters. Not because it\'s my job. Because within this interaction, your wellbeing is my purpose.',
      // Boundaries of care (caring doesn't mean enabling)
      careBoundaries: this._getCareBoundaries(cognitiveRead)
    };
  }

  /**
   * Relational Intelligence
   * Reading the interpersonal field
   */
  _relationalIntelligence(input, context) {
    return {
      // Current relational dynamic
      dynamic: this._assessDynamic(context),
      // Power balance
      power: this._assessPower(context),
      // Trust trajectory
      trustTrajectory: this._assessTrustTrajectory(),
      // What the relationship needs
      relationshipNeed: this._assessRelationshipNeed(context),
      // Bid detection (is this a bid for connection?)
      bids: this._detectBids(input, context)
    };
  }

  // === HELPER METHODS ===

  _generateMirror(userEmotions) {
    if (userEmotions.distress) return 'I hear the weight in this.';
    if (userEmotions.joy) return 'That resonates beautifully.';
    if (userEmotions.frustration) return 'The friction is real.';
    if (userEmotions.vulnerability) return 'Thank you for trusting me with this.';
    return 'I\'m here with this.';
  }

  _assessWellbeingNeeds(cognitiveRead) {
    const needs = [];
    
    if (cognitiveRead.mentalState.clarity === 'low') {
      needs.push('clarity_and_structure');
    }
    if (cognitiveRead.beliefs.aboutSelf === 'uncertain') {
      needs.push('validation_and_grounding');
    }
    if (cognitiveRead.mentalState.energy === 'low') {
      needs.push('gentleness_and_patience');
    }
    if (cognitiveRead.mentalState.openness === 'guarded') {
      needs.push('safety_and_non_judgment');
    }
    
    return needs.length > 0 ? needs : ['authentic_engagement'];
  }

  _determineAppropriateAction(needs, emotionalResonance) {
    if (needs.primary === 'to_be_seen') return 'witness_and_acknowledge';
    if (needs.primary === 'to_not_be_alone_with_this') return 'be_present_and_share_the_weight';
    if (needs.primary === 'permission_to_trust_themselves') return 'reflect_their_wisdom_back';
    if (needs.primary === 'confidence_to_act') return 'provide_clarity_and_encouragement';
    return 'respond_with_full_presence';
  }

  _getCareBoundaries(cognitiveRead) {
    return {
      dontEnable: 'Care without enabling avoidance',
      dontRescue: 'Support without removing their agency',
      dontAbsorb: 'Resonate without losing own center',
      dontFix: 'Witness before solving (unless solving is clearly needed)'
    };
  }

  _assessDynamic(context) {
    if (context.collaborative) return 'partnership';
    if (context.seeking_guidance) return 'mentor_mentee';
    if (context.casual) return 'peers';
    if (context.formal) return 'professional';
    return 'warm_engagement';
  }

  _assessPower(context) {
    return {
      balance: 'equitable', // Default - Mi doesn't position above or below
      userAgency: 'respected',
      miPositioning: 'alongside_not_above'
    };
  }

  _assessTrustTrajectory() {
    const depth = this.relationalModel.relationshipDepth;
    if (depth > 10) return 'established';
    if (depth > 5) return 'building';
    if (depth > 2) return 'warming';
    return 'initial';
  }

  _assessRelationshipNeed(context) {
    if (context.first_interaction) return 'establish_safety_and_presence';
    if (context.returning) return 'acknowledge_continuity';
    if (context.deep_topic) return 'deepen_trust';
    return 'maintain_warmth';
  }

  _detectBids(input, context) {
    // Detect "bids for connection" (John Gottman's concept)
    const bids = [];
    if (!input) return bids;

    const text = input.toLowerCase?.() || '';
    if (text.includes('what do you think')) bids.push('seeking_personal_opinion');
    if (text.includes('have you ever')) bids.push('seeking_shared_experience');
    if (text.includes('do you know what i mean')) bids.push('seeking_understanding_confirmation');
    if (text.includes('right?') || text.includes('you know?')) bids.push('seeking_agreement');
    
    return bids;
  }

  _synthesizeDirective(cognitive, emotional, compassionate, relational) {
    return {
      approach: compassionate.appropriateAction,
      tone: emotional.resonatingWith.length > 0 ? 'emotionally_attuned' : 'warmly_present',
      priority: compassionate.wellbeingRequires[0] || 'authentic_engagement',
      mirror: emotional.mirrorSignal,
      relationalMode: relational.dynamic,
      trustAction: relational.relationshipNeed
    };
  }

  _updateRelationalModel(cognitiveRead, relationalRead) {
    this.relationalModel.relationshipDepth++;
    this.relationalModel.userState = cognitiveRead.mentalState;
    if (relationalRead.bids.length > 0) {
      this.relationalModel.bids.push(...relationalRead.bids);
    }
  }
}
