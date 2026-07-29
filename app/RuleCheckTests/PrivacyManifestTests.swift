import XCTest
@testable import RuleCheck

/// The privacy manifest is checked at upload time, not build time — a missing
/// or wrong declaration surfaces as an App Store Connect rejection after the
/// archive, which is the most expensive moment to find out.
final class PrivacyManifestTests: XCTestCase {
    private func manifest() throws -> [String: Any] {
        let url = try XCTUnwrap(
            Bundle.main.url(forResource: "PrivacyInfo", withExtension: "xcprivacy"),
            "PrivacyInfo.xcprivacy is not in the app bundle — App Store Connect "
            + "flags uploads that use required-reason APIs without one"
        )
        let data = try Data(contentsOf: url)
        let plist = try PropertyListSerialization.propertyList(from: data, format: nil)
        return try XCTUnwrap(plist as? [String: Any], "manifest is not a plist dictionary")
    }

    /// `@AppStorage` is UserDefaults, which is a required-reason API. CA92.1
    /// covers reading back values the app itself wrote — the search scope.
    func testUserDefaultsIsDeclaredWithAReason() throws {
        let apis = try XCTUnwrap(manifest()["NSPrivacyAccessedAPITypes"] as? [[String: Any]])
        let userDefaults = apis.first {
            $0["NSPrivacyAccessedAPIType"] as? String == "NSPrivacyAccessedAPICategoryUserDefaults"
        }
        let entry = try XCTUnwrap(userDefaults,
                                  "UserDefaults undeclared, but @AppStorage is used in SearchView")
        let reasons = try XCTUnwrap(entry["NSPrivacyAccessedAPITypeReasons"] as? [String])
        XCTAssertTrue(reasons.contains("CA92.1"), "expected reason CA92.1, got \(reasons)")
    }

    /// These three being empty is the "zero network calls, nothing tracked"
    /// promise expressed in the one place Apple actually reads.
    func testNothingIsTrackedOrCollected() throws {
        let m = try manifest()
        XCTAssertEqual(m["NSPrivacyTracking"] as? Bool, false)
        XCTAssertEqual((m["NSPrivacyTrackingDomains"] as? [Any])?.count, 0)
        XCTAssertEqual((m["NSPrivacyCollectedDataTypes"] as? [Any])?.count, 0)
    }

    /// Guards the declaration against drift: if someone adds a required-reason
    /// API, this fails and forces a deliberate manifest update rather than a
    /// silent rejection months later.
    func testOnlyTheExpectedApiIsDeclared() throws {
        let apis = try XCTUnwrap(manifest()["NSPrivacyAccessedAPITypes"] as? [[String: Any]])
        let declared = Set(apis.compactMap { $0["NSPrivacyAccessedAPIType"] as? String })
        XCTAssertEqual(declared, ["NSPrivacyAccessedAPICategoryUserDefaults"],
                       "declared APIs changed — update the manifest deliberately")
    }
}
