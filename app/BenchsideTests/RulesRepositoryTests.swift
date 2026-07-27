import XCTest
@testable import Benchside

final class RulesRepositoryTests: XCTestCase {
    var repo: RulesRepository!
    override func setUpWithError() throws { repo = try RulesRepository.bundled() }

    func testDocumentsListsAllThree() throws {
        let ids = try repo.documents().map(\.id).sorted()
        XCTAssertEqual(ids, ["penalty-guidelines", "tcg-rules", "tournament-rules"])
    }
    func testSearchReturnsSnippetedHits() throws {
        let hits = try repo.search("energy", scope: .all)
        XCTAssertFalse(hits.isEmpty)
        XCTAssertFalse(hits[0].snippet.isEmpty)
    }
    func testScopeFilterExcludesOtherDocs() throws {
        let hits = try repo.search("deck", scope: .tournament)
        XCTAssertFalse(hits.isEmpty)
        XCTAssertTrue(hits.allSatisfy { ["tournament-rules", "penalty-guidelines"].contains($0.section.docId) })
    }
    func testSearchSnippetsCarryMatchMarkers() throws {
        let hits = try repo.search("asleep", scope: .all)
        let marked = hits.filter { $0.snippet.contains(SnippetHighlighter.start) }
        XCTAssertFalse(marked.isEmpty, "FTS match ranges must reach the app as sentinel markers")
        let s = try XCTUnwrap(marked.first).snippet
        XCTAssertEqual(s.filter { $0 == SnippetHighlighter.start }.count,
                       s.filter { $0 == SnippetHighlighter.end }.count,
                       "markers must be balanced")
    }
    func testGarbageQueryDoesNotThrow() throws {
        XCTAssertTrue(try repo.search("\"asleep AND (", scope: .all).count >= 0)
        XCTAssertEqual(try repo.search("   ", scope: .all).count, 0)
    }
    func testDocumentOutlineIsOrdered() throws {
        let sections = try repo.sections(inDocument: "tournament-rules")
        XCTAssertEqual(sections.count, 119)
        XCTAssertEqual(sections.map(\.sortOrder), sections.map(\.sortOrder).sorted())
    }
    func testSectionNeighborsAndXrefs() throws {
        let sec = try XCTUnwrap(repo.section(id: "pen-5.6.1"))
        XCTAssertEqual(sec.docId, "penalty-guidelines")
        let (prev, next) = try repo.neighbors(of: sec)
        XCTAssertNotNil(prev); XCTAssertNotNil(next)
        let refs = try repo.crossReferences(from: "trh-1")  // any id; just must not throw
        XCTAssertNotNil(refs)
    }
}
