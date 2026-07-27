import XCTest

final class SmokeTests: XCTestCase {
    func testBundledDatabasePresent() throws {
        let url = Bundle(for: Self.self).url(forResource: "benchside", withExtension: "db")
            ?? Bundle.main.url(forResource: "benchside", withExtension: "db")
        XCTAssertNotNil(url, "benchside.db must be bundled — run `just app-db` before building")
    }
}
