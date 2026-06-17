import Foundation

// MARK: - Enums

public enum AgentRole: String, Codable, CaseIterable, Sendable {
    case orchestrator
    case researcher
    case coder
    case executor
    case critic
    case designer
    case writer
    case debugger
    case planner
}

public enum TaskStatus: String, Codable, Sendable {
    case pending
    case running
    case awaitingApproval = "awaiting_approval"
    case completed
    case failed
    case cancelled
}

public enum TaskComplexity: String, Codable, Sendable {
    case light, medium, heavy
}

// MARK: - Models

public struct Playbook: Codable, Identifiable, Sendable {
    public let id: String
    public let title: String
    public let description: String
    public let status: TaskStatus
    public let steps: [PlaybookStep]
    public let createdAt: Date
    public let completedAt: Date?
    public let error: String?

    enum CodingKeys: String, CodingKey {
        case id, title, description, status, steps, error
        case createdAt = "created_at"
        case completedAt = "completed_at"
    }
}

public struct PlaybookStep: Codable, Identifiable, Sendable {
    public let id: String
    public let description: String
    public let agentRole: AgentRole?
    public let dependsOn: [String]
    public let complexity: TaskComplexity
    public let toolsNeeded: [String]
    public let status: TaskStatus?
    public let result: String?

    enum CodingKeys: String, CodingKey {
        case id, description, complexity, status, result
        case agentRole = "agent_role"
        case dependsOn = "depends_on"
        case toolsNeeded = "tools_needed"
    }
}

public struct PlaybookCreate: Codable, Sendable {
    public let title: String
    public let description: String
    public let rawText: String?
    public let autoExecute: Bool

    enum CodingKeys: String, CodingKey {
        case title, description
        case rawText = "raw_text"
        case autoExecute = "auto_execute"
    }

    public init(title: String, description: String, rawText: String? = nil, autoExecute: Bool = true) {
        self.title = title
        self.description = description
        self.rawText = rawText
        self.autoExecute = autoExecute
    }
}

public struct AgentState: Codable, Identifiable, Sendable {
    public let id: String
    public let role: AgentRole
    public let name: String
    public let status: String
    public let currentTask: String?
    public let thoughts: [String]
    public let actionsTaken: Int
    public let progress: Double
    public let model: String
    public let avatarColor: String

    enum CodingKeys: String, CodingKey {
        case id, role, name, status, thoughts, progress, model
        case currentTask = "current_task"
        case actionsTaken = "actions_taken"
        case avatarColor = "avatar_color"
    }
}

public struct ChatMessage: Codable, Identifiable, Sendable {
    public let id: String
    public let sessionId: String
    public let role: String
    public let content: String
    public let model: String?
    public let tokensUsed: Int
    public let createdAt: Date

    enum CodingKeys: String, CodingKey {
        case id, role, content, model
        case sessionId = "session_id"
        case tokensUsed = "tokens_used"
        case createdAt = "created_at"
    }
}

public struct HealthResponse: Codable, Sendable {
    public let status: String
    public let version: String
    public let services: ServiceStatus
    public let uptimeSeconds: Double

    enum CodingKeys: String, CodingKey {
        case status, version, services
        case uptimeSeconds = "uptime_seconds"
    }
}

public struct ServiceStatus: Codable, Sendable {
    public let ollama: String
    public let chromadb: String
    public let redis: String
    public let database: String
}

public struct StreamEvent: Codable, Sendable {
    public let eventType: String
    public let agentId: String?
    public let agentRole: AgentRole?
    public let data: [String: AnyCodable]
    public let timestamp: Date

    enum CodingKeys: String, CodingKey {
        case data, timestamp
        case eventType = "event_type"
        case agentId = "agent_id"
        case agentRole = "agent_role"
    }
}

// MARK: - Helper for Any JSON values

public struct AnyCodable: Codable, Sendable {
    public let value: Any

    public init(_ value: Any) {
        self.value = value
    }

    public init(from decoder: Decoder) throws {
        let container = try decoder.singleValueContainer()
        if let intVal = try? container.decode(Int.self) {
            value = intVal
        } else if let doubleVal = try? container.decode(Double.self) {
            value = doubleVal
        } else if let stringVal = try? container.decode(String.self) {
            value = stringVal
        } else if let boolVal = try? container.decode(Bool.self) {
            value = boolVal
        } else {
            value = ""
        }
    }

    public func encode(to encoder: Encoder) throws {
        var container = encoder.singleValueContainer()
        if let intVal = value as? Int {
            try container.encode(intVal)
        } else if let doubleVal = value as? Double {
            try container.encode(doubleVal)
        } else if let stringVal = value as? String {
            try container.encode(stringVal)
        } else if let boolVal = value as? Bool {
            try container.encode(boolVal)
        }
    }
}
