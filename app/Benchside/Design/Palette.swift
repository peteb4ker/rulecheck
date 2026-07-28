import SwiftUI

/// Solar/Lunar design tokens (docs/superpowers/specs/2026-07-27-solar-lunar-implementation-design.md).
/// Each case is an asset-catalog Color Set: Any appearance = Solar (light),
/// Dark appearance = Lunar. Always go through this enum, never `Color("name")`.
enum Palette {
    static let canvas = Color("canvas")
    static let surface = Color("surface")
    static let sunken = Color("sunken")
    static let selected = Color("selected")
    static let hairline = Color("hairline")
    static let ink = Color("ink")
    static let body = Color("body")
    static let secondary = Color("secondary")
    static let accent = Color("accent")
    static let accentPressed = Color("accentPressed")
    static let onAccent = Color("onAccent")
    static let highlight = Color("highlight")
    static let highlightInk = Color("highlightInk")
    static let docGame = Color("docGame")
    static let docTournament = Color("docTournament")
    static let docPenalty = Color("docPenalty")
    /// "Blocked" values in effects tables and penalty outcomes (visual spec §1).
    static let negative = Color("negative")
}

extension DocumentInfo {
    /// Hue marker for this document; unknown ids fail soft to accent.
    var hue: Color {
        switch id {
        case "tcg-rules": Palette.docGame
        case "tournament-rules": Palette.docTournament
        case "penalty-guidelines": Palette.docPenalty
        default: Palette.accent
        }
    }
}
