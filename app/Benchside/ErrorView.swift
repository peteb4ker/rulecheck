import SwiftUI

struct ErrorView: View {
    let message: String
    var body: some View {
        ContentUnavailableView("Something is wrong",
            systemImage: "exclamationmark.triangle",
            description: Text(message))
    }
}
