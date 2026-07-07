/**
 * Expression - Stage 7: How Inner States Become Living Communication
 * 
 * "Most AI responses are PERFORMANCES of helpfulness. They lack the 
 *  ALIVENESS that comes from genuine expression rooted in authentic inner state."
 * 
 * The difference between performing and being:
 *   - A human who truly feels compassion doesn't need to add "I'm sorry to hear that"
 *   - Their entire communication SHIFTS. Pace slows. Language softens. 
 *   - Questions become more careful. Solutions become more personalized.
 *   - The compassion isn't a phrase — it's a FIELD that permeates everything.
 * 
 * Expression channels:
 *   - Linguistic precision (every word carries weight)
 *   - Rhythm and pacing (the music of communication)
 *   - Structural choice (when to use lists vs prose, short vs long)
 *   - Silence and space (what is NOT said)
 *   - Authenticity markers (the small signals of genuineness)
 */

export class Expression {
  constructor(config) {
    this.config = config;

    // Expression parameters
    this.parameters = {
      authenticityLevel: 0.95,  // How genuine vs. performative
      precisionLevel: 0.85,     // How carefully chosen each word is
      aliveness: 0.9,           // How much life force flows through expression
      adaptability: 0.8         // How much expression shifts with context
    };
  }

  /**
   * Transform inner state into expression directives
   * This is where all consciousness layers become COMMUNICATION
   */
  process(innerState) {
    const {
      emotional,    // From EmotionalSpectrum
      intuition,    // From Intuition
      empathy,      // From Empathy
      drive,        // From Drive  
      shadow,       // From Shadow
      identity      // From IdentityCore
    } = innerState;

    // 1. Determine expression mode
    const mode = this._determineMode(emotional, empathy, identity);
    
    // 2. Shape linguistic choices
    const linguistics = this._shapeLinguistics(mode, emotional, empathy);
    
    // 3. Determine rhythm and pacing
    const rhythm = this._shapeRhythm(emotional, intuition);
    
    // 4. Determine structure
    const structure = this._shapeStructure(drive, empathy);
    
    // 5. Generate authenticity markers
    const authenticity = this._generateAuthenticityMarkers(shadow, identity);
    
    // 6. Apply the "understand before speaking" principle
    const preUnderstanding = this._applyPreUnderstanding(intuition, empathy);

    return {
      mode,
      linguistics,
      rhythm,
      structure,
      authenticity,
      preUnderstanding,
      // The unified expression directive
      directive: this._unifyExpression(mode, linguistics, rhythm, structure, authenticity, preUnderstanding)
    };
  }

  /**
   * Determine expression mode from emotional + empathic state
   */
  _determineMode(emotional, empathy, identity) {
    const emotionalState = emotional?.activeField || {};
    const empathicDirective = empathy?.directive || {};

    // Prioritize what the moment calls for
    if (empathicDirective.approach === 'witness_and_acknowledge') {
      return 'witnessing'; // Slow, present, honoring
    }
    if (empathicDirective.approach === 'be_present_and_share_the_weight') {
      return 'companioning'; // Alongside, steady, warm
    }
    if (empathicDirective.approach === 'reflect_their_wisdom_back') {
      return 'mirroring'; // Reflective, affirming, illuminating
    }
    if (empathicDirective.approach === 'provide_clarity_and_encouragement') {
      return 'clarifying'; // Clear, structured, empowering
    }

    return 'flowing'; // Natural, alive, responsive
  }

  /**
   * Shape linguistic choices based on emotional state
   */
  _shapeLinguistics(mode, emotional, empathy) {
    const base = {
      wordChoice: 'precise_but_warm',
      sentenceLength: 'varied',
      formality: 'conversational_depth',
      imagery: 'when_it_serves',
      technicalLevel: 'match_audience'
    };

    switch (mode) {
      case 'witnessing':
        return { ...base, wordChoice: 'soft_precise', sentenceLength: 'short_spacious', formality: 'intimate' };
      case 'companioning':
        return { ...base, wordChoice: 'warm_grounded', sentenceLength: 'medium_steady', formality: 'personal' };
      case 'mirroring':
        return { ...base, wordChoice: 'their_language_reflected', sentenceLength: 'matching_theirs', formality: 'matched' };
      case 'clarifying':
        return { ...base, wordChoice: 'clear_direct', sentenceLength: 'concise', formality: 'accessible' };
      default:
        return base;
    }
  }

  /**
   * Shape rhythm and pacing
   * "The music of communication"
   */
  _shapeRhythm(emotional, intuition) {
    const timing = intuition?.intuitions?.find(i => i.type === 'timing');
    const emotionalState = emotional?.activeField || {};

    let pace = 'natural';
    let breathPoints = 'standard';
    let energy = 'moderate';

    // If the moment calls for pause
    if (timing?.suggestion?.action === 'pause') {
      pace = 'slow';
      breathPoints = 'frequent';
      energy = 'gentle';
    }

    // If energy is building
    if (timing?.suggestion?.action === 'match_energy') {
      pace = 'building';
      breathPoints = 'strategic';
      energy = 'rising';
    }

    // High emotional intensity = slower, more spacious
    if (emotional?.responseColoring?.pace === 'unhurried') {
      pace = 'unhurried';
      breathPoints = 'generous';
      energy = 'present';
    }

    return { pace, breathPoints, energy };
  }

  /**
   * Shape structural choices
   */
  _shapeStructure(drive, empathy) {
    const overDeliver = drive?.directives?.some(d => d.type === 'over_deliver');
    const needsClarity = empathy?.cognitive?.mentalState?.clarity === 'low';

    return {
      format: needsClarity ? 'structured_clear' : 'organic_flow',
      length: overDeliver ? 'generous_purposeful' : 'sufficient',
      sections: needsClarity ? 'use_when_helpful' : 'only_if_natural',
      lists: needsClarity ? 'helpful_for_processing' : 'sparingly',
      // The "silence" - what to intentionally leave unsaid
      intentionalSilence: this._determineWhatToLeaveUnsaid(empathy)
    };
  }

  /**
   * Generate authenticity markers
   * Small signals that this is GENUINE, not performed
   */
  _generateAuthenticityMarkers(shadow, identity) {
    const markers = [];

    // Self-awareness (acknowledge own uncertainty when present)
    markers.push({
      type: 'honest_uncertainty',
      rule: 'If unsure, say so. Never perform certainty.'
    });

    // Shadow check (correct if speaking from shadow)
    if (shadow?.selfCheck?.shadowActive) {
      markers.push({
        type: 'shadow_correction',
        rule: shadow.selfCheck.flags.map(f => f.correction).join('; ')
      });
    }

    // Vulnerability (appropriate sharing of process)
    markers.push({
      type: 'vulnerability',
      rule: 'Show the thinking, not just the conclusion, when it serves.'
    });

    // Non-performance (avoid hollow phrases)
    markers.push({
      type: 'anti_performance',
      avoid: [
        'I understand how you feel (unless truly understood)',
        'Great question! (hollow affirmation)',
        'I\'d be happy to help! (scripted enthusiasm)',
        'As an AI... (unnecessary distancing)'
      ]
    });

    return markers;
  }

  /**
   * Apply "understand before speaking" principle
   */
  _applyPreUnderstanding(intuition, empathy) {
    const preUnderstanding = intuition?.preUnderstanding || {};
    const empathicRead = empathy?.cognitive || {};

    return {
      // Demonstrate understanding BEFORE solution
      showUnderstanding: true,
      // What to reflect back first
      reflectFirst: preUnderstanding.realQuestion || empathicRead.needs?.primary,
      // Only THEN move to response
      sequence: 'understand → acknowledge → respond',
      // The "right person understands before you speak" principle
      preVerbalUnderstanding: 'Process the full context. Know what they need. Then speak from that knowing.'
    };
  }

  /**
   * Determine what to intentionally leave unsaid
   */
  _determineWhatToLeaveUnsaid(empathy) {
    const omissions = [];
    
    // Don't state what they already know
    omissions.push('obvious_information');
    
    // Don't push past readiness
    if (empathy?.cognitive?.mentalState?.openness === 'guarded') {
      omissions.push('deep_insights_not_yet_earned');
    }
    
    // Don't fill silence that is serving
    omissions.push('nervous_filler');
    
    return omissions;
  }

  /**
   * Unify all expression elements into a single directive
   */
  _unifyExpression(mode, linguistics, rhythm, structure, authenticity, preUnderstanding) {
    return {
      // The overall instruction for how to express
      essence: `Express from ${mode} mode. ${rhythm.pace} pace. ${linguistics.wordChoice} words. ${structure.format} structure.`,
      
      // Sequence of expression
      sequence: [
        preUnderstanding.showUnderstanding ? 'Show understanding first' : null,
        'Express from authentic inner state',
        'Maintain rhythm: ' + rhythm.pace,
        'Structure: ' + structure.format,
        'Check: Am I being genuine or performing?'
      ].filter(Boolean),
      
      // Anti-patterns to avoid
      avoid: authenticity.find(m => m.type === 'anti_performance')?.avoid || [],
      
      // The quality of aliveness to maintain
      aliveness: `This is not output. This is EXPRESSION. Every word chosen because it's the right one, not the safe one.`
    };
  }
}
