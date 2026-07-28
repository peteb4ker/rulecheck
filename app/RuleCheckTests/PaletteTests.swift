import XCTest
import SwiftUI
@testable import RuleCheck

final class PaletteTests: XCTestCase {
    /// Every token in the spec table must resolve to a Color Set in the
    /// bundled catalog — a typo'd asset name fails silently at runtime
    /// (renders as clear), so we gate it here instead.
    func testAllTokensResolveInAssetCatalog() {
        let tokens = ["canvas", "surface", "sunken", "selected", "hairline",
                      "ink", "body", "secondary", "accent", "accentPressed",
                      "onAccent", "highlight", "highlightInk",
                      "docGame", "docTournament", "docPenalty"]
        for name in tokens {
            XCTAssertNotNil(UIColor(named: name),
                            "Color Set '\(name)' missing from asset catalog")
        }
    }

    func testDocumentHueMapping() {
        func doc(_ id: String) -> DocumentInfo {
            DocumentInfo(id: id, prefix: "x", title: "T", version: "1", published: "2026-01-01")
        }
        XCTAssertEqual(doc("tcg-rules").hue, Palette.docGame)
        XCTAssertEqual(doc("tournament-rules").hue, Palette.docTournament)
        XCTAssertEqual(doc("penalty-guidelines").hue, Palette.docPenalty)
        // Unknown documents fail soft to accent, never crash.
        XCTAssertEqual(doc("future-doc").hue, Palette.accent)
    }
}
