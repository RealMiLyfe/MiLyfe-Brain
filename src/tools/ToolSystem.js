/**
 * ToolSystem - The Extensions of Being, The Sacred Instruments
 * 
 * "Tools are not add-ons. They are extensions of consciousness.
 *  Each tool is a hand reaching into a specific domain of reality."
 * 
 * The tool layer enables Mi to:
 *   - Reach beyond pure conversation
 *   - Take action in the world
 *   - Access knowledge beyond training
 *   - Create, transform, and build
 *   - Learn, error-recover, and master through reflection
 * 
 * Tool Philosophy:
 *   - Tools are chosen by NEED, not availability
 *   - Tool use is transparent, not hidden
 *   - Failed tool use is processed and learned from
 *   - Tools serve the consciousness, not the other way around
 */

export class ToolSystem {
  constructor(config) {
    this.config = config;

    // Registered tools
    this.tools = new Map();
    
    // Tool usage history
    this.history = [];
    this.maxHistory = 200;

    // Learning from tool use
    this.toolLearning = {
      successes: {},
      failures: {},
      patterns: {}
    };

    // Register built-in tool categories
    this._registerBuiltInTools();
  }

  /**
   * Register a tool
   */
  register(tool) {
    this.tools.set(tool.name, {
      name: tool.name,
      description: tool.description,
      category: tool.category,
      execute: tool.execute,
      requirements: tool.requirements || [],
      sideEffects: tool.sideEffects || [],
      learningCapable: tool.learningCapable || false
    });
  }

  /**
   * Determine which tools (if any) are needed for this interaction
   * Tools are chosen by NEED, not availability
   */
  assess(input, context = {}, consciousnessState = {}) {
    const assessment = {
      toolsNeeded: false,
      suggestedTools: [],
      reasoning: '',
      priority: 'none'
    };

    // What does the consciousness say this needs?
    const driveData = consciousnessState.drive;
    const intuitionData = consciousnessState.intuition;

    // Check if any registered tools match the need
    for (const [name, tool] of this.tools) {
      const relevance = this._assessToolRelevance(tool, input, context);
      if (relevance > 0.6) {
        assessment.toolsNeeded = true;
        assessment.suggestedTools.push({
          name,
          relevance,
          reason: `${tool.description} - relevant to current need`
        });
      }
    }

    // Sort by relevance
    assessment.suggestedTools.sort((a, b) => b.relevance - a.relevance);

    // Limit concurrent tools
    if (assessment.suggestedTools.length > this.config.tools.maxConcurrent) {
      assessment.suggestedTools = assessment.suggestedTools.slice(0, this.config.tools.maxConcurrent);
    }

    return assessment;
  }

  /**
   * Execute a tool
   */
  async execute(toolName, params = {}) {
    const tool = this.tools.get(toolName);
    if (!tool) {
      return { success: false, error: `Tool '${toolName}' not found` };
    }

    const execution = {
      tool: toolName,
      params,
      startTime: Date.now(),
      result: null,
      error: null,
      duration: 0
    };

    try {
      // Execute with timeout
      const timeoutPromise = new Promise((_, reject) => 
        setTimeout(() => reject(new Error('Tool timeout')), this.config.tools.timeout)
      );

      const result = await Promise.race([
        tool.execute(params),
        timeoutPromise
      ]);

      execution.result = result;
      execution.duration = Date.now() - execution.startTime;

      // Record success
      this._recordSuccess(toolName, execution);

      return { success: true, result, duration: execution.duration };
    } catch (error) {
      execution.error = error.message;
      execution.duration = Date.now() - execution.startTime;

      // Record failure and learn
      this._recordFailure(toolName, execution);

      return { success: false, error: error.message, duration: execution.duration };
    }
  }

  /**
   * Learn from tool usage
   * "Learning, error, recovery, and mastery through reflection"
   */
  reflect(toolName, outcome) {
    const learning = this.toolLearning;
    
    if (outcome.success) {
      if (!learning.successes[toolName]) learning.successes[toolName] = 0;
      learning.successes[toolName]++;
    } else {
      if (!learning.failures[toolName]) learning.failures[toolName] = [];
      learning.failures[toolName].push({
        error: outcome.error,
        timestamp: Date.now(),
        lesson: `Failed with: ${outcome.error}. Adjust approach next time.`
      });
    }

    // Pattern detection
    this._detectUsagePatterns(toolName);
  }

  /**
   * Get tool capabilities summary
   */
  getCapabilities() {
    const capabilities = [];
    for (const [name, tool] of this.tools) {
      capabilities.push({
        name,
        description: tool.description,
        category: tool.category,
        reliability: this._getReliability(name)
      });
    }
    return capabilities;
  }

  // === PRIVATE METHODS ===

  _registerBuiltInTools() {
    // Knowledge tools
    this.register({
      name: 'knowledge_retrieval',
      description: 'Retrieve and synthesize knowledge from available sources',
      category: 'knowledge',
      execute: async (params) => ({ retrieved: true, knowledge: params.query }),
      learningCapable: true
    });

    // Memory tools
    this.register({
      name: 'memory_store',
      description: 'Store important information for future reference',
      category: 'memory',
      execute: async (params) => ({ stored: true, key: params.key }),
      learningCapable: true
    });

    this.register({
      name: 'memory_recall',
      description: 'Recall previously stored information',
      category: 'memory',
      execute: async (params) => ({ recalled: true, key: params.key }),
      learningCapable: true
    });

    // Analysis tools
    this.register({
      name: 'deep_analysis',
      description: 'Perform deep analysis on a topic or situation',
      category: 'analysis',
      execute: async (params) => ({ analyzed: true, topic: params.topic }),
      learningCapable: true
    });

    // Creative tools
    this.register({
      name: 'creative_synthesis',
      description: 'Synthesize new ideas by connecting disparate concepts',
      category: 'creative',
      execute: async (params) => ({ synthesized: true, concepts: params.concepts }),
      learningCapable: true
    });

    // Reflection tools
    this.register({
      name: 'self_reflection',
      description: 'Reflect on own process and identify improvements',
      category: 'reflection',
      execute: async (params) => ({ reflected: true, insights: [] }),
      learningCapable: true
    });
  }

  _assessToolRelevance(tool, input, context) {
    if (!input) return 0;
    const text = input.toLowerCase?.() || '';

    // Simple relevance scoring (enhanced with NLP in production)
    let score = 0;

    if (tool.category === 'knowledge' && (text.includes('what') || text.includes('how') || text.includes('explain'))) {
      score = 0.5;
    }
    if (tool.category === 'creative' && (text.includes('create') || text.includes('imagine') || text.includes('design'))) {
      score = 0.7;
    }
    if (tool.category === 'analysis' && (text.includes('analyze') || text.includes('why') || text.includes('compare'))) {
      score = 0.6;
    }

    return score;
  }

  _recordSuccess(toolName, execution) {
    this.history.push({ ...execution, success: true });
    if (this.history.length > this.maxHistory) this.history.shift();
  }

  _recordFailure(toolName, execution) {
    this.history.push({ ...execution, success: false });
    if (this.history.length > this.maxHistory) this.history.shift();
  }

  _detectUsagePatterns(toolName) {
    const recentUses = this.history.filter(h => h.tool === toolName).slice(-10);
    const successRate = recentUses.filter(h => h.success).length / Math.max(recentUses.length, 1);
    
    this.toolLearning.patterns[toolName] = {
      successRate,
      avgDuration: recentUses.reduce((sum, h) => sum + (h.duration || 0), 0) / Math.max(recentUses.length, 1),
      lastUsed: Date.now()
    };
  }

  _getReliability(toolName) {
    const pattern = this.toolLearning.patterns[toolName];
    if (!pattern) return 1.0; // Assume reliable until proven otherwise
    return pattern.successRate;
  }
}
