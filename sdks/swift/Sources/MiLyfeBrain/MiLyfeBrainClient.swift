import Foundation

/// MiLyfe Brain Swift SDK Client for iOS/macOS.
///
/// Usage:
/// ```swift
/// let client = MiLyfeBrainClient(baseURL: "http://localhost:8200")
/// let health = try await client.health()
/// let playbook = try await client.createPlaybook(.init(title: "My Task", description: "Do something"))
/// ```
public actor MiLyfeBrainClient {
    private let baseURL: URL
    private let session: URLSession
    private let apiKey: String?
    private let decoder: JSONDecoder

    public init(baseURL: String, apiKey: String? = nil, timeout: TimeInterval = 300) {
        self.baseURL = URL(string: baseURL)!
        self.apiKey = apiKey

        let config = URLSessionConfiguration.default
        config.timeoutIntervalForRequest = timeout
        self.session = URLSession(configuration: config)

        self.decoder = JSONDecoder()
        self.decoder.dateDecodingStrategy = .iso8601
    }

    private func makeRequest(_ method: String, path: String, body: Data? = nil) -> URLRequest {
        var request = URLRequest(url: baseURL.appendingPathComponent(path))
        request.httpMethod = method
        request.setValue("application/json", forHTTPHeaderField: "Content-Type")
        if let apiKey {
            request.setValue(apiKey, forHTTPHeaderField: "X-API-Key")
        }
        request.httpBody = body
        return request
    }

    private func perform<T: Decodable>(_ request: URLRequest) async throws -> T {
        let (data, response) = try await session.data(for: request)
        guard let httpResponse = response as? HTTPURLResponse else {
            throw MiLyfeBrainError.networkError("Invalid response")
        }
        guard (200...299).contains(httpResponse.statusCode) else {
            let detail = (try? JSONDecoder().decode([String: String].self, from: data))?["detail"] ?? "Unknown error"
            throw MiLyfeBrainError.apiError(httpResponse.statusCode, detail)
        }
        return try decoder.decode(T.self, from: data)
    }

    // MARK: - Health

    public func health() async throws -> HealthResponse {
        let request = makeRequest("GET", path: "/health")
        return try await perform(request)
    }

    // MARK: - Playbooks

    public func createPlaybook(_ create: PlaybookCreate) async throws -> Playbook {
        let body = try JSONEncoder().encode(create)
        let request = makeRequest("POST", path: "/api/playbooks/", body: body)
        return try await perform(request)
    }

    public func listPlaybooks() async throws -> [Playbook] {
        let request = makeRequest("GET", path: "/api/playbooks/")
        return try await perform(request)
    }

    public func getPlaybook(id: String) async throws -> Playbook {
        let request = makeRequest("GET", path: "/api/playbooks/\(id)")
        return try await perform(request)
    }

    public func deletePlaybook(id: String) async throws {
        let request = makeRequest("DELETE", path: "/api/playbooks/\(id)")
        let (_, response) = try await session.data(for: request)
        guard let httpResponse = response as? HTTPURLResponse,
              (200...299).contains(httpResponse.statusCode) else {
            throw MiLyfeBrainError.apiError(0, "Delete failed")
        }
    }

    // MARK: - Agents

    public func listActiveAgents() async throws -> [AgentState] {
        let request = makeRequest("GET", path: "/api/agents/active")
        return try await perform(request)
    }

    public func spawnAgent(role: AgentRole, task: String) async throws -> AgentState {
        let body = try JSONEncoder().encode(["role": role.rawValue, "task": task])
        let request = makeRequest("POST", path: "/api/agents/spawn", body: body)
        return try await perform(request)
    }

    // MARK: - Chat

    public func chat(message: String, sessionId: String? = nil) async throws -> ChatMessage {
        var payload: [String: String] = ["message": message]
        if let sessionId { payload["session_id"] = sessionId }
        let body = try JSONEncoder().encode(payload)
        let request = makeRequest("POST", path: "/api/chat/send", body: body)
        return try await perform(request)
    }

    public func getChatHistory(sessionId: String) async throws -> [ChatMessage] {
        let request = makeRequest("GET", path: "/api/chat/history/\(sessionId)")
        return try await perform(request)
    }

    // MARK: - Streaming (AsyncSequence)

    public func streamEvents() -> AsyncThrowingStream<StreamEvent, Error> {
        AsyncThrowingStream { continuation in
            Task {
                var request = makeRequest("GET", path: "/api/stream/sse")
                request.setValue("text/event-stream", forHTTPHeaderField: "Accept")

                let (bytes, _) = try await session.bytes(for: request)
                for try await line in bytes.lines {
                    if line.hasPrefix("data: ") {
                        let jsonStr = String(line.dropFirst(6))
                        if let data = jsonStr.data(using: .utf8),
                           let event = try? self.decoder.decode(StreamEvent.self, from: data) {
                            continuation.yield(event)
                        }
                    }
                }
                continuation.finish()
            }
        }
    }
}

// MARK: - Errors

public enum MiLyfeBrainError: Error, LocalizedError {
    case networkError(String)
    case apiError(Int, String)
    case decodingError(String)

    public var errorDescription: String? {
        switch self {
        case .networkError(let msg): return "Network error: \(msg)"
        case .apiError(let code, let detail): return "API error \(code): \(detail)"
        case .decodingError(let msg): return "Decoding error: \(msg)"
        }
    }
}
