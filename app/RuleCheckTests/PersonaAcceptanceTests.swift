import XCTest
@testable import RuleCheck

final class PersonaAcceptanceTests: XCTestCase {
    func testPlayerAsleepTopHit() throws {
        let hits = try RulesRepository.bundled().search("asleep", scope: .all)
        let top = try XCTUnwrap(hits.first).section
        XCTAssertEqual(top.docId, "tcg-rules")
        XCTAssertTrue(top.title.localizedCaseInsensitiveContains("asleep"))
    }
    func testJudgeDeckCheckTopHit() throws {
        let hits = try RulesRepository.bundled().search("deck check", scope: .tournament)
        let top = try XCTUnwrap(hits.first).section
        // Spec anchor: relevant tournament-doc section, citable by number.
        // No section in the corpus is titled "Deck Check"; the handbook's
        // §4.3.1 "Legality Checks" is the deck-check procedure section.
        XCTAssertTrue(["tournament-rules", "penalty-guidelines"].contains(top.docId))
        XCTAssertNotNil(top.citableNumber, "judge must be able to cite by number")
        let text = (top.title + " " + top.body).localizedLowercase
        XCTAssertTrue(text.contains("deck") && text.contains("check"),
                      "top hit must actually concern deck checks; got \(top.id)")
    }
}
