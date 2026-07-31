import Foundation

/// The authored structure behind a section — what the reader renders.
///
/// Decoded leniently on purpose: an entry that gains a field the app does
/// not know about yet should render what it can rather than failing. The
/// pipeline is the schema authority; the app is a renderer.
struct RuleStructure: Decodable, Hashable {
    enum Archetype: String, Decodable {
        case mechanic, procedure, penalty, definition, note
    }

    struct BranchOption: Decodable, Hashable, Identifiable {
        let condition: String
        let outcome: String
        let detail: String?
        var id: String { condition + outcome }
    }

    struct Branch: Decodable, Hashable {
        let when: String
        let options: [BranchOption]
    }

    struct Step: Decodable, Hashable, Identifiable {
        let actor: String?
        let action: String
        let note: String?
        var id: String { action }
    }

    struct PenaltyRow: Decodable, Hashable, Identifiable {
        let tier: String
        let penalty: String
        let note: String?
        let examples: [String]?
        var id: String { tier }
    }

    struct Term: Decodable, Hashable, Identifiable {
        let term: String
        let meaning: String
        var id: String { term }
    }

    let archetype: Archetype
    let summary: String?

    // mechanic
    let state: [String]?
    let branch: Branch?
    let endsWhen: [String]?
    let effects: [String: String]?

    // procedure
    let steps: [Step]?

    // penalty
    let infraction: String?
    let handling: [String]?
    let examples: [String]?
    let basePenalty: [PenaltyRow]?
    let upgradeConditions: [String]?

    // definition / note
    let terms: [Term]?
    let paragraphs: [String]?

    /// Load-bearing official phrasing the author declared and the pipeline
    /// verified appears verbatim in the source. The only verbatim text the
    /// research gate allows the app to surface.
    let quotes: [String]?

    /// Glyphs derived at build time, parallel to the field each annotates.
    ///
    /// Optional throughout, and never trusted for length. A database built
    /// before glyphs existed simply has none, and the reader renders exactly
    /// as it did before.
    let stateGlyphs: [GlyphMark?]?
    let effectGlyphs: [GlyphMark?]?
    let branchGlyphs: [GlyphMark?]?
    let stepGlyphs: [GlyphMark?]?

    enum CodingKeys: String, CodingKey {
        case archetype, summary, state, branch, effects, steps, infraction
        case handling, examples, terms, paragraphs, quotes
        case endsWhen = "ends_when"
        case basePenalty = "base_penalty"
        case upgradeConditions = "upgrade_conditions"
        case stateGlyphs = "state_glyphs"
        case effectGlyphs = "effect_glyphs"
        case branchGlyphs = "branch_glyphs"
        case stepGlyphs = "step_glyphs"
    }

    /// `effects` in a stable order — dictionaries do not preserve one, and a
    /// truth table that reshuffles between launches is disorienting.
    var orderedEffects: [(label: String, value: String)] {
        (effects ?? [:]).sorted { $0.key < $1.key }.map { (label: $0.key, value: $0.value) }
    }

    static func decode(_ json: String?) -> RuleStructure? {
        guard let json, let data = json.data(using: .utf8) else { return nil }
        return try? JSONDecoder().decode(RuleStructure.self, from: data)
    }
}
