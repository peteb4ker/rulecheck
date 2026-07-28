import SwiftUI

struct ErrorView: View {
    let message: String
    var body: some View {
        ContentUnavailableView {
            Label("Something is wrong", systemImage: "exclamationmark.triangle")
                .foregroundStyle(Palette.ink)
        } description: {
            Text(message)
                .foregroundStyle(Palette.body)
        }
        .tint(Palette.accent)
    }
}
