import SwiftUI

/// A mark standing beside a structured row: a symbol, or a chip of the word.
///
/// Everything about how a glyph looks is decided in the lexicon and shipped in
/// the database. The app draws what it is given and looks nothing up, so the
/// whole mapping stays reviewable in one place and the app degrades by simply
/// not drawing anything it cannot understand.
struct GlyphMark: Decodable, Hashable {
    /// The concept, used for the accessibility label. A glyph that stands in
    /// for a word still has to be readable aloud.
    let name: String
    let symbol: String?
    let chip: String?
    let tint: String?

    /// Design tokens only. A tint names a `Palette` case rather than a colour,
    /// so chips follow Solar and Lunar and dark mode comes free. An unknown
    /// name falls back to the accent rather than failing to draw.
    var color: Color {
        switch tint {
        case "negative": Palette.negative
        case "positive": Palette.positive
        case "secondary": Palette.secondary
        case "accent": Palette.accent
        default: Palette.accent
        }
    }
}

struct GlyphView: View {
    let glyph: GlyphMark

    var body: some View {
        Group {
            if let chip = glyph.chip, !chip.isEmpty {
                Text(chip)
                    .font(.caption2.weight(.bold))
                    .tracking(0.4)
                    .foregroundStyle(glyph.color)
                    .padding(.horizontal, 6)
                    .padding(.vertical, 2)
                    .background(glyph.color.opacity(0.15),
                                in: Capsule(style: .continuous))
                    .lineLimit(1)
            } else if let symbol = glyph.symbol, !symbol.isEmpty {
                Image(systemName: symbol)
                    .font(.footnote.weight(.semibold))
                    .foregroundStyle(glyph.color)
                    .frame(minWidth: 18)
            }
        }
        .accessibilityLabel(glyph.name)
    }
}

extension Array where Element == GlyphMark? {
    /// The glyph for one row, or nil.
    ///
    /// Guards the index rather than trusting it. A pipeline bug that produced
    /// a short or long array would otherwise crash a reader mid-game, which is
    /// the one place this app must not fail.
    func at(_ index: Int) -> GlyphMark? {
        indices.contains(index) ? self[index] : nil
    }
}
