import XCTest

final class RuleCheckUITests: XCTestCase {
    func testAppLaunchesSearchReady() {
        let app = XCUIApplication()
        app.launch()
        // Search is focused on launch (spec) — the field is the launch signal.
        XCTAssertTrue(app.searchFields.firstMatch.waitForExistence(timeout: 10))
        XCTAssertTrue(app.buttons["Tournament"].waitForExistence(timeout: 5))
    }

    /// #22: the field is focused at launch, so typing works with no tap.
    /// iOS 17 has no API to focus a `.searchable` field — no autofocus there.
    func testSearchIsFocusedAtLaunch() throws {
        guard #available(iOS 18.0, *) else {
            throw XCTSkip("searchFocused requires iOS 18")
        }
        let app = XCUIApplication()
        app.launch()
        XCTAssertTrue(app.searchFields.firstMatch.waitForExistence(timeout: 10))
        XCTAssertTrue(app.keyboards.firstMatch.waitForExistence(timeout: 5),
                      "keyboard must be up at launch — no tap required")
        app.typeText("asleep")
        XCTAssertEqual(app.searchFields.firstMatch.value as? String, "asleep")
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
        // Opt out of launch autofocus: while search is active iOS owns the
        // nav bar's trailing item, so About isn't reachable without first
        // tapping a dismiss button whose label is Apple's and differs across
        // iOS versions. Probing for it raced on CI and went red on main.
        // Autofocus itself is covered by testSearchIsFocusedAtLaunch.
        app.launchArguments += ["-disableSearchAutofocus"]
        app.launch()
        XCTAssertTrue(app.searchFields.firstMatch.waitForExistence(timeout: 10))
        let about = app.buttons["About"].firstMatch
        XCTAssertTrue(about.waitForExistence(timeout: 5))
        about.tap()
        XCTAssertTrue(app.staticTexts
            .containing(NSPredicate(format: "label CONTAINS %@", "not affiliated with"))
            .firstMatch.waitForExistence(timeout: 5))
    }
}
