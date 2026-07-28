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
    /// The authored structure, when this section has one. Sections without
    /// it fall back to prose rendering.
    let structure: RuleStructure?
    /// Rulebook "numbers" are full title text ("3 Card Types"), so a
    /// leading digit is not enough — a citation must look like 4 or 5.6.1,
    /// otherwise the reader renders the title twice.
    var citableNumber: String? {
        let isSectionNumber = number.range(
            of: #"^\d+(\.\d+)*$"#, options: .regularExpression) != nil
        return isSectionNumber ? number : nil
    }
}

struct SearchHit: Identifiable, Hashable {
    let section: RuleSection
    let snippet: String
    var id: String { section.id }
}

/// Navigation targets. A NavigationStack's typed path can only carry one
/// type — pushing a DocumentInfo into a [String] path silently does
/// nothing, which is exactly the bug that made document cards inert.
enum Route: Hashable {
    case section(String)
    case document(DocumentInfo)
}
