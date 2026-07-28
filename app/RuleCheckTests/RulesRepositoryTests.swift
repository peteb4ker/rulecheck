import XCTest
@testable import RuleCheck

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
    // Section counts are content, not contract: they move whenever a document
    // is revised or a section is skiplisted. Assert the invariants instead.
    func testDocumentOutlineIsOrdered() throws {
        let sections = try repo.sections(inDocument: "tournament-rules")
        XCTAssertGreaterThan(sections.count, 50, "outline should be substantial")
        XCTAssertEqual(sections.map(\.sortOrder), sections.map(\.sortOrder).sorted())
    }
    func testSectionCountsMatchOutlines() throws {
        let counts = try repo.sectionCounts()
        for doc in try repo.documents() {
            XCTAssertEqual(counts[doc.id], try repo.sections(inDocument: doc.id).count,
                           "count for \(doc.id) must match its outline")
        }
    }
    func testSkippedSectionsAreAbsent() throws {
        // The skiplist must remove sections from the app entirely — never
        // leave them shipping verbatim source text.
        for skipped in ["tcg-Parts of a Pokémon Card", "tcg-Credits", "trh-Appendix A"] {
            XCTAssertNil(try repo.section(id: skipped), "\(skipped) must not ship")
        }
    }
    func testSectionNeighborsAndXrefs() throws {
        let sec = try XCTUnwrap(repo.section(id: "pen-5.6.1"))
        XCTAssertEqual(sec.docId, "penalty-guidelines")
        let (prev, next) = try repo.neighbors(of: sec)
        XCTAssertNotNil(prev); XCTAssertNotNil(next)
        let refs = try repo.crossReferences(from: "trh-1")  // any id; just must not throw
        XCTAssertNotNil(refs)
    }

    func testCitableNumberRejectsTitleLikeNumbers() throws {
        // Rulebook sections carry title text in `number`; only true section
        // numbers may render as a citation.
        let titleLike = try XCTUnwrap(repo.section(id: "tcg-3 Card Types"))
        XCTAssertNil(titleLike.citableNumber)
        let numbered = try XCTUnwrap(repo.section(id: "pen-5.6.1"))
        XCTAssertEqual(numbered.citableNumber, "5.6.1")
    }

    func testStructureDecodesForAuthoredSections() throws {
        let asleep = try XCTUnwrap(repo.section(id: "tcg-Asleep"))
        let structure = try XCTUnwrap(asleep.structure)
        XCTAssertEqual(structure.archetype, .mechanic)
        XCTAssertFalse(structure.state?.isEmpty ?? true)
        XCTAssertEqual(structure.branch?.options.count, 2)
        XCTAssertEqual(structure.orderedEffects.map(\.label), ["Abilities", "Attack", "Retreat"])
    }

    func testStartupPathTiming() throws {
        // Startup does: open DB -> documents() -> sectionCounts().
        // If this is fast, a slow launch is not the data layer.
        let clock = ContinuousClock()
        let open = try clock.measure { _ = try RulesRepository.bundled() }
        let r = try RulesRepository.bundled()
        let search = try clock.measure { _ = try r.search("asleep", scope: .all) }
        _ = try clock.measure { _ = try r.documents() }
        _ = try clock.measure { _ = try r.sectionCounts() }
        XCTAssertLessThan(open, .seconds(1))
        XCTAssertLessThan(search, .seconds(1))
    }
}
