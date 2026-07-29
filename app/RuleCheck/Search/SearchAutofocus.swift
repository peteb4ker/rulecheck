import SwiftUI

/// Puts the cursor in the search field at launch — the spec's "open the app,
/// start typing" promise.
///
/// `searchFocused` is iOS 18+. On iOS 17 there is no API to focus a
/// `.searchable` field, so the fallback is simply no autofocus: the field is
/// still one tap away. That degradation is deliberate, not an oversight.
private struct SearchAutofocus: ViewModifier {
    @FocusState private var focused: Bool

    /// UI tests that aren't about autofocus opt out. While search is active
    /// iOS replaces the nav bar's trailing item with its own dismiss button,
    /// so a test reaching for About otherwise has to find and tap that button
    /// first — whose label is not ours and varies by iOS version. Opting out
    /// removes the guesswork instead of racing it.
    static let disableArgument = "-disableSearchAutofocus"

    private var autofocusDisabled: Bool {
        ProcessInfo.processInfo.arguments.contains(Self.disableArgument)
    }

    @ViewBuilder
    func body(content: Content) -> some View {
        if #available(iOS 18.0, *), !autofocusDisabled {
            content
                .searchFocused($focused)
                .onAppear { focused = true }
        } else {
            content
        }
    }
}

extension View {
    /// Apply to the view carrying `.searchable` — focus binds to that field.
    func searchAutofocus() -> some View { modifier(SearchAutofocus()) }
}
