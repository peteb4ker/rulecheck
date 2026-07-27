import SwiftUI

/// Solar/Lunar design tokens (docs/superpowers/specs/2026-07-27-solar-lunar-implementation-design.md).
/// Each case is an asset-catalog Color Set: Any appearance = Solar (light),
/// Dark appearance = Lunar. Always go through this enum, never `Color("name")`.
enum Palette {
    static let highlight = Color("highlight")
    static let highlightInk = Color("highlightInk")
}
