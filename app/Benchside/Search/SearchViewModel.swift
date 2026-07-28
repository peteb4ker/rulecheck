import Foundation
import Observation

@Observable
final class SearchViewModel {
    private let repository: RulesRepository
    var query: String = ""
    var scope: SearchScope = .all
    private(set) var groups: [(doc: DocumentInfo, hits: [SearchHit])] = []
    private(set) var documents: [DocumentInfo] = []
    private(set) var sectionCounts: [String: Int] = [:]
    private(set) var errorMessage: String?

    init(repository: RulesRepository) {
        self.repository = repository
        refresh()
    }

    func refresh() {
        do {
            documents = try repository.documents()
            sectionCounts = try repository.sectionCounts()
            let trimmed = query.trimmingCharacters(in: .whitespaces)
            guard !trimmed.isEmpty else { groups = []; return }
            let hits = try repository.search(trimmed, scope: scope)
            let byDoc = Dictionary(grouping: hits, by: \.section.docId)
            groups = documents.compactMap { doc in
                byDoc[doc.id].map { (doc: doc, hits: $0) }
            }
            errorMessage = nil
        } catch {
            groups = []; errorMessage = error.localizedDescription
        }
    }
}
