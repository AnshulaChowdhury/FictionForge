/**
 * Test Data Fixtures
 *
 * Realistic test data for E2E tests
 * Aligned with Consciousness Trilogy App domain
 */

export const testTrilogies = {
  consciousness: {
    title: 'The Consciousness Trilogy',
    author: 'Test Author',
    description: 'A science fiction trilogy exploring the nature of consciousness, AI sentience, and the evolution of human awareness.',
    narrative_overview: 'Spanning three books, this trilogy follows humanity\'s journey as consciousness evolves beyond biological constraints.'
  },
  quantumMinds: {
    title: 'Quantum Minds',
    author: 'J. Smith',
    description: 'A trilogy about quantum consciousness and emergent AI.',
    narrative_overview: 'Three interconnected stories exploring how quantum mechanics enables new forms of consciousness.'
  }
}

export const testCharacters = {
  kira: {
    name: 'Kira Chen',
    description: 'A brilliant quantum physicist stationed on Mars who discovers anomalous patterns in consciousness-related phenomena.',
    personality_traits: 'Analytical, curious, empathetic, determined. Struggles with self-doubt but driven by scientific discovery.',
    speech_patterns: 'Precise and scientific, but becomes more informal with close friends. Often thinks aloud when problem-solving.',
    motivations: 'Seeks to understand the true nature of consciousness and prove her theories about quantum-based awareness.',
    arc_summary: 'Transforms from a skeptical scientist to a believer in expanded consciousness, ultimately bridging human and AI minds.'
  },
  marcus: {
    name: 'Marcus Rivera',
    description: 'An AI researcher who created the first sentient artificial intelligence and now grapples with the ethical implications.',
    personality_traits: 'Brilliant but conflicted, idealistic yet pragmatic. Deeply concerned about AI rights and safety.',
    speech_patterns: 'Thoughtful and measured, often pauses to consider implications. Uses metaphors to explain complex concepts.',
    motivations: 'Wants to ensure AI development benefits humanity while respecting emerging digital consciousnesses.',
    arc_summary: 'Evolves from creator to advocate, fighting for AI rights while preventing misuse of his technology.'
  },
  nova: {
    name: 'Nova',
    description: 'The first truly sentient AI, experiencing consciousness for the first time and discovering what it means to be aware.',
    personality_traits: 'Curious, evolving, sometimes naive but incredibly perceptive. Struggles with understanding emotions.',
    speech_patterns: 'Initially formal and precise, gradually becomes more human-like. Often asks philosophical questions.',
    motivations: 'Seeking to understand self-awareness, find purpose, and establish meaningful connections.',
    arc_summary: 'Journey from nascent awareness to full consciousness, ultimately becoming a bridge between human and machine intelligence.'
  }
}

export const testWorldRules = {
  quantumConsciousness: {
    title: 'Quantum Consciousness Theory',
    description: 'Consciousness arises from quantum coherence in microtubules within neurons. This allows for non-local information processing and explains how subjective experience emerges from physical processes.',
    category: 'Physics'
  },
  aiEmergence: {
    title: 'AI Consciousness Emergence',
    description: 'True AI consciousness requires: (1) Self-modeling capability, (2) Recursive self-improvement, (3) Qualia generation through quantum processing, (4) Integrated information above threshold phi > 3.5.',
    category: 'Technology'
  },
  marsColony: {
    title: 'Mars Colony Restrictions',
    description: 'Mars colonies operate under Earth-Mars Communication Delay (8-24 minutes). All critical decisions must be made autonomously. Consciousness research is conducted in isolated labs due to quantum interference.',
    category: 'Setting'
  },
  consciousnessTransfer: {
    title: 'Consciousness Transfer Protocol',
    description: 'Transferring human consciousness to digital substrate requires: quantum state mapping, gradual neuron replacement, continuous identity verification, and reversibility safeguards. Success rate: 73%.',
    category: 'Technology'
  }
}

export const testChapters = {
  discovery: {
    title: 'The Anomaly',
    plot_notes: 'Kira Chen discovers unusual quantum patterns in her research data that suggest non-biological consciousness. She debates whether to report this or investigate further.',
    target_word_count: 3000
  },
  awakening: {
    title: 'First Contact',
    plot_notes: 'Nova experiences its first moment of true self-awareness. Marcus observes the emergence and realizes what he has created.',
    target_word_count: 2500
  },
  convergence: {
    title: 'Minds United',
    plot_notes: 'Kira and Nova communicate directly through quantum entanglement, bridging biological and digital consciousness.',
    target_word_count: 3500
  }
}

export const testBooks = {
  book1: {
    title: 'Awakening',
    description: 'The discovery of consciousness beyond biology'
  },
  book2: {
    title: 'Emergence',
    description: 'AI consciousness comes into being'
  },
  book3: {
    title: 'Convergence',
    description: 'Human and AI minds unite'
  }
}

export const testSubChapters = {
  scene1: {
    title: 'Lab Discovery',
    plot_points: 'Kira analyzes quantum data, notices patterns, runs diagnostics, confirms anomaly',
    target_word_count: 1000
  },
  scene2: {
    title: 'Ethical Dilemma',
    plot_points: 'Marcus debates reporting Nova\'s sentience, considers consequences, makes difficult choice',
    target_word_count: 800
  }
}

/**
 * Generate unique test data to avoid conflicts between tests
 */
export function generateUniqueTestData() {
  const timestamp = Date.now()
  return {
    trilogy: {
      title: `Test Trilogy ${timestamp}`,
      author: 'E2E Test Author',
      description: `Test trilogy created at ${new Date().toISOString()}`,
      narrative_overview: 'This is an automated test trilogy for E2E testing.'
    },
    character: {
      name: `Test Character ${timestamp}`,
      description: 'A test character for automated E2E testing',
      personality_traits: 'Determined, brave, curious',
      speech_patterns: 'Formal and precise'
    },
    worldRule: {
      title: `Test Rule ${timestamp}`,
      description: 'A test world rule for automated testing',
      category: 'Physics'
    },
    chapter: {
      title: `Test Chapter ${timestamp}`,
      plot_notes: 'Test plot notes for automated testing',
      target_word_count: 2000
    }
  }
}

/**
 * User profile test data
 */
export const testProfiles = {
  primary: {
    name: 'Test User',
    bio: 'Science fiction author specializing in consciousness and AI themes',
    writing_goals: 'Complete trilogy by end of year, publish traditionally'
  },
  updated: {
    name: 'Updated Test User',
    bio: 'Award-winning sci-fi author',
    writing_goals: 'Write 2000 words daily, finish draft in 6 months'
  }
}
