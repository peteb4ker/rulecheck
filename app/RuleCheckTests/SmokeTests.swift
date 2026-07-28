import XCTest

final class SmokeTests: XCTestCase {
    func testBundledDatabasePresent() throws {
        let url = Bundle(for: Self.self).url(forResource: "rulecheck", withExtension: "db")
            ?? Bundle.main.url(forResource: "rulecheck", withExtension: "db")
        XCTAssertNotNil(url, "rulecheck.db must be bundled — run `just app-db` before building")
    }
}
