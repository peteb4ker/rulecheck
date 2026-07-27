import Foundation

enum SearchScope: String, CaseIterable {
    case all, game, tournament
    var docIds: [String]? {
        switch self {
        case .all: return nil
        case .game: return ["tcg-rules"]
        case .tournament: return ["tournament-rules", "penalty-guidelines"]
        }
    }
    var label: String {
        switch self {
        case .all: return "All"
        case .game: return "Game Rules"
        case .tournament: return "Tournament"
        }
    }
}

struct DocumentInfo: Identifiable, Hashable {
    let id: String, prefix: String, title: String, version: String, published: String
}

struct RuleSection: Identifiable, Hashable {
    let id: String, docId: String
    let parentId: String?
    let number: String, title: String, body: String, breadcrumb: String
    let sortOrder: Int
    /// tcg-rules "numbers" are full title text — only treat as citable when numeric.
    var citableNumber: String? { number.first?.isNumber == true ? number : nil }
}

struct SearchHit: Identifiable, Hashable {
    let section: RuleSection
    let snippet: String
    var id: String { section.id }
}
