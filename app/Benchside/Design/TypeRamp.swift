import SwiftUI

/// Solar/Lunar type ramp helpers. Text styles only — never fixed point
/// sizes — so Dynamic Type keeps working at every size.
extension View {
    /// SECTION LABEL style: caps mono caption, wide tracking, secondary.
    func sectionLabelStyle() -> some View {
        self.font(.caption2.monospaced().weight(.semibold))
            .kerning(1.2)
            .textCase(.uppercase)
            .foregroundStyle(Palette.secondary)
    }

    /// Citation/breadcrumb style: monospaced caption (the judge flavour).
    func citationStyle() -> some View {
        self.font(.caption.monospaced().weight(.medium))
    }
}
