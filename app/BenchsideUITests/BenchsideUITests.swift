import XCTest

final class BenchsideUITests: XCTestCase {
    func testAppLaunchesSearchReady() {
        let app = XCUIApplication()
        app.launch()
        // Search is focused on launch (spec) — the field is the launch signal.
        XCTAssertTrue(app.searchFields.firstMatch.waitForExistence(timeout: 10))
        XCTAssertTrue(app.buttons["Tournament"].waitForExistence(timeout: 5))
    }

    func testTypingLandsInSearchField() {
        let app = XCUIApplication()
        app.launch()
        let field = app.searchFields.firstMatch
        XCTAssertTrue(field.waitForExistence(timeout: 10))
        field.tap()
        field.typeText("asleep")
        XCTAssertEqual(field.value as? String, "asleep",
                       "typed text must land in the search field")
    }

    func testPlayerSearchAsleepAndRead() {
        let app = XCUIApplication()
        app.launch()
        let field = app.searchFields.firstMatch
        XCTAssertTrue(field.waitForExistence(timeout: 10))
        field.tap()
        field.typeText("asleep")
        // Result rows merge their texts into one accessibility element.
        let hit = app.cells
            .containing(NSPredicate(format: "label CONTAINS %@", "Asleep"))
            .firstMatch
        XCTAssertTrue(hit.waitForExistence(timeout: 5))
        hit.tap()
        // Reader shows the section title and the document version footer.
        XCTAssertTrue(app.staticTexts
            .containing(NSPredicate(format: "label CONTAINS %@", "version"))
            .firstMatch.waitForExistence(timeout: 5))
    }

    func testAboutShowsDisclaimer() {
        let app = XCUIApplication()
        app.launch()
        let cancel = app.buttons["Cancel"].firstMatch
        if cancel.waitForExistence(timeout: 3) { cancel.tap() }
        let about = app.buttons["About"].firstMatch
        XCTAssertTrue(about.waitForExistence(timeout: 5))
        about.tap()
        XCTAssertTrue(app.staticTexts
            .containing(NSPredicate(format: "label CONTAINS %@", "not affiliated with"))
            .firstMatch.waitForExistence(timeout: 5))
    }
}
