import Foundation

enum QuerySanitizer {
    /// Lowercase alphanumeric tokens, each emitted as a quoted prefix match.
    /// User input never reaches FTS5 raw.
    static func ftsMatch(_ raw: String) -> String? {
        let tokens = raw.lowercased()
            .components(separatedBy: CharacterSet.alphanumerics.inverted)
            .filter { !$0.isEmpty }
        guard !tokens.isEmpty else { return nil }
        return tokens.map { "\"\($0)\"*" }.joined(separator: " ")
    }
}
