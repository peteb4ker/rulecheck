import XCTest
@testable import Benchside

/// The judge affordance (#50): declared official wording plus a citation
/// precise enough to look up in the source document.
final class CitationTests: XCTestCase {
    private let doc = DocumentInfo(id: "trh", prefix: "TRH",
                                   title: "Tournament Rules Handbook",
                                   version: "2026.1", published: "2026-05-21")

    private func section(number: String, structure: RuleStructure? = nil) -> RuleSection {
        RuleSection(id: "trh-1", docId: "trh", parentId: nil, number: number,
                    title: "Deck Checks", body: "", breadcrumb: "TRH › Deck Checks",
                    sortOrder: 0, structure: structure)
    }

    func testCitationCarriesSectionNumberWhenCitable() {
        XCTAssertEqual(
            SectionView.citation(for: section(number: "5.6.1"), in: doc),
            "Tournament Rules Handbook — version 2026.1, 2026-05-21 · § 5.6.1")
    }

    func testCitationOmitsNumberWhenNotCitable() {
        // Titles-as-numbers ("3 Card Types") are not citations.
        XCTAssertEqual(
            SectionView.citation(for: section(number: "3 Card Types"), in: doc),
            "Tournament Rules Handbook — version 2026.1, 2026-05-21")
    }

    func testQuotesDecodeFromStructure() {
        let json = """
        {"archetype":"note","tier":"judge","summary":"s","paragraphs":["p"],
         "quotes":["the exact official phrasing"]}
        """
        let structure = RuleStructure.decode(json)
        XCTAssertEqual(structure?.quotes, ["the exact official phrasing"])
    }

    func testStructureWithoutQuotesDecodesToNil() {
        let json = """
        {"archetype":"note","tier":"judge","summary":"s","paragraphs":["p"]}
        """
        XCTAssertNil(RuleStructure.decode(json)?.quotes)
    }
}
