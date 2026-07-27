import XCTest
@testable import Benchside

final class SnippetHighlighterTests: XCTestCase {
    private func highlightRuns(_ a: AttributedString) -> [(range: Range<AttributedString.Index>, text: String)] {
        a.runs.compactMap { run in
            run.backgroundColor != nil ? (run.range, String(a.characters[run.range])) : nil
        }
    }

    func testPlainTextPassesThrough() {
        let a = SnippetHighlighter.attributed("no markers here")
        XCTAssertEqual(String(a.characters), "no markers here")
        XCTAssertTrue(highlightRuns(a).isEmpty)
    }

    func testSingleMatchGetsHighlightRun() {
        let a = SnippetHighlighter.attributed(
            "An Active card that is \u{E000}Asleep\u{E001} is turned sideways.")
        XCTAssertEqual(String(a.characters),
                       "An Active card that is Asleep is turned sideways.")
        let runs = highlightRuns(a)
        XCTAssertEqual(runs.count, 1)
        XCTAssertEqual(runs.first?.text, "Asleep")
    }

    func testMultipleMatchesEachGetARun() {
        let a = SnippetHighlighter.attributed(
            "\u{E000}deck\u{E001} and \u{E000}check\u{E001} both match")
        XCTAssertEqual(String(a.characters), "deck and check both match")
        XCTAssertEqual(highlightRuns(a).map(\.text), ["deck", "check"])
    }

    func testUnclosedMarkerDegradesToPlainText() {
        let a = SnippetHighlighter.attributed("ends \u{E000}without close")
        XCTAssertEqual(String(a.characters), "ends without close")
        XCTAssertTrue(highlightRuns(a).isEmpty)
    }

    func testStrayEndMarkerIsDropped() {
        let a = SnippetHighlighter.attributed("stray\u{E001} end")
        XCTAssertEqual(String(a.characters), "stray end")
        XCTAssertTrue(highlightRuns(a).isEmpty)
    }
}
