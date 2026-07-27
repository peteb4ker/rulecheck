import XCTest
@testable import Benchside

final class QuerySanitizerTests: XCTestCase {
    func testPlainWordsBecomeQuotedPrefixTokens() {
        XCTAssertEqual(QuerySanitizer.ftsMatch("deck check"), "\"deck\"* \"check\"*")
    }
    func testFtsSyntaxIsNeutralized() {
        XCTAssertEqual(QuerySanitizer.ftsMatch("\"asleep AND ("), "\"asleep\"* \"and\"*")
    }
    func testCurlyQuotesAndHyphensSurvive() {
        XCTAssertEqual(QuerySanitizer.ftsMatch("play-pokemon’s"), "\"play\"* \"pokemon\"* \"s\"*")
    }
    func testEmptyOrSymbolOnlyReturnsNil() {
        XCTAssertNil(QuerySanitizer.ftsMatch("   "))
        XCTAssertNil(QuerySanitizer.ftsMatch("(*)"))
    }
}
