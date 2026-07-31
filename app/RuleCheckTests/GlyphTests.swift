import XCTest
@testable import RuleCheck

/// The app draws what the pipeline gives it and looks nothing up, so these
/// pin the decoding and the ways it is allowed to fail.
final class GlyphTests: XCTestCase {

    private func structure(_ json: String) -> RuleStructure? {
        RuleStructure.decode(json)
    }

    func testASectionWithNoGlyphArraysDecodesAsBefore() throws {
        // A database built before glyphs existed must render exactly as it did.
        let s = try XCTUnwrap(structure("""
        {"archetype":"mechanic","summary":"s","state":["No attacking"]}
        """))
        XCTAssertNil(s.stateGlyphs)
        XCTAssertEqual(s.state?.count, 1)
    }

    func testGlyphArraysDecode() throws {
        let s = try XCTUnwrap(structure("""
        {"archetype":"mechanic","summary":"s","state":["No attacking","Sideways"],
         "state_glyphs":[{"name":"blocked","symbol":"nosign"},null]}
        """))
        XCTAssertEqual(s.stateGlyphs?.count, 2)
        XCTAssertEqual(s.stateGlyphs?.at(0)?.name, "blocked")
        XCTAssertEqual(s.stateGlyphs?.at(0)?.symbol, "nosign")
        XCTAssertNil(s.stateGlyphs?.at(1))
    }

    func testAChipDecodes() throws {
        let s = try XCTUnwrap(structure("""
        {"archetype":"mechanic","summary":"s","state":["Abilities"],
         "state_glyphs":[{"name":"ability","chip":"ABILITY","tint":"negative"}]}
        """))
        XCTAssertEqual(s.stateGlyphs?.at(0)?.chip, "ABILITY")
        XCTAssertEqual(s.stateGlyphs?.at(0)?.tint, "negative")
    }

    func testAShortArrayIsIgnoredRatherThanCrashing() throws {
        // The one that protects a player mid-game from a pipeline bug.
        let s = try XCTUnwrap(structure("""
        {"archetype":"mechanic","summary":"s","state":["a","b","c"],
         "state_glyphs":[{"name":"blocked","symbol":"nosign"}]}
        """))
        XCTAssertNotNil(s.stateGlyphs?.at(0))
        XCTAssertNil(s.stateGlyphs?.at(1))
        XCTAssertNil(s.stateGlyphs?.at(9))
    }

    func testALongArrayIsIgnoredRatherThanCrashing() throws {
        let s = try XCTUnwrap(structure("""
        {"archetype":"mechanic","summary":"s","state":["a"],
         "state_glyphs":[{"name":"blocked","symbol":"nosign"},
                         {"name":"asleep","symbol":"moon.zzz"}]}
        """))
        XCTAssertNotNil(s.stateGlyphs?.at(0))
        XCTAssertNotNil(s.stateGlyphs?.at(1))
    }

    func testAnUnknownTintFallsBackRatherThanFailingToDraw() {
        let glyph = GlyphMark(name: "x", symbol: nil, chip: "X", tint: "chartreuse")
        XCTAssertEqual(glyph.color, Palette.accent)
    }

    func testKnownTintsResolveToTheirTokens() {
        XCTAssertEqual(GlyphMark(name: "a", symbol: nil, chip: "A", tint: "negative").color,
                       Palette.negative)
        XCTAssertEqual(GlyphMark(name: "a", symbol: nil, chip: "A", tint: "positive").color,
                       Palette.positive)
        XCTAssertEqual(GlyphMark(name: "a", symbol: nil, chip: "A", tint: "secondary").color,
                       Palette.secondary)
    }

    func testTheRealDatabaseCarriesGlyphs() throws {
        // Against the shipped database, not a fixture: the Asleep rule is the
        // player persona's acceptance case and must carry marks.
        let repo = try RulesRepository.bundled()
        let section = try XCTUnwrap(repo.section(id: "tcg-Asleep"))
        let s = try XCTUnwrap(section.structure)
        XCTAssertNotNil(s.stateGlyphs, "the shipped DB has no glyphs on tcg-Asleep")
        XCTAssertEqual(s.stateGlyphs?.compactMap { $0 }.count, 2,
                       "expected the two blocked rows to carry a glyph")
    }
}
