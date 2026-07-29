import UIKit
import XCTest
@testable import RuleCheck

/// The app's shipped identity. These keys are easy to lose silently:
/// GENERATE_INFOPLIST_FILE synthesizes them from build settings and discards
/// whatever Info.plist says, so a missing setting produces a build with the
/// key absent entirely — which App Store Connect rejects on upload, long
/// after the mistake was made.
final class BundleIdentityTests: XCTestCase {
    private var appInfo: [String: Any] {
        // Unit tests host inside the app, so main bundle is the app bundle.
        Bundle.main.infoDictionary ?? [:]
    }

    func testBundleIdentifierIsTheReservedOne() {
        XCTAssertEqual(Bundle.main.bundleIdentifier, "app.rulecheck.RuleCheck")
    }

    func testDisplayNameIsTheTwoWordPublicName() {
        // "RuleCheck" (one word) is a live, unrelated App Store app.
        XCTAssertEqual(appInfo["CFBundleDisplayName"] as? String, "Rule Check")
    }

    /// A build with no app icon is rejected on upload, not at build time.
    func testAppIconIsCompiledIntoTheBundle() throws {
        let icons = try XCTUnwrap(appInfo["CFBundleIcons"] as? [String: Any],
                                  "no CFBundleIcons — the AppIcon set did not compile")
        let primary = try XCTUnwrap(icons["CFBundlePrimaryIcon"] as? [String: Any])
        let files = try XCTUnwrap(primary["CFBundleIconFiles"] as? [String])
        XCTAssertFalse(files.isEmpty, "CFBundleIconFiles is empty")
        XCTAssertNotNil(UIImage(named: files[0]), "icon \(files[0]) is not loadable")
    }

    /// Without this key every upload stalls on the export-compliance
    /// question. False is correct here and provable: the app has no network
    /// code and no cryptography beyond what the OS does for itself.
    func testExportComplianceIsDeclared() {
        XCTAssertEqual(appInfo["ITSAppUsesNonExemptEncryption"] as? Bool, false)
    }

    func testVersionKeysArePresentAndWellFormed() throws {
        let short = try XCTUnwrap(appInfo["CFBundleShortVersionString"] as? String,
                                  "CFBundleShortVersionString missing — App Store Connect rejects this")
        let build = try XCTUnwrap(appInfo["CFBundleVersion"] as? String,
                                  "CFBundleVersion missing — App Store Connect rejects this")
        XCTAssertNotNil(short.range(of: #"^\d+(\.\d+){0,2}$"#, options: .regularExpression),
                        "marketing version must look like 1 / 1.0 / 1.0.0, got \(short)")
        XCTAssertNotNil(Int(build), "build number must be an integer, got \(build)")
    }
}
