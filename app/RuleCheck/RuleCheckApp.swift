import SwiftUI

@main
struct RuleCheckApp: App {
    var body: some Scene {
        WindowGroup { AppRoot() }
    }
}

struct AppRoot: View {
    // The view model must be created once and owned here: constructing it
    // inline in body would mint a fresh model (empty query, lost focus) on
    // every re-render — e.g. when the keyboard changes the safe area.
    @State private var loaded: (repo: RulesRepository, model: SearchViewModel)?
    @State private var loadError: Error?

    var body: some View {
        Group {
            if let loaded {
                SearchView(model: loaded.model, repository: loaded.repo)
            } else if let loadError {
                ErrorView(message: loadError.localizedDescription)
            } else {
                ProgressView().task {
                    do {
                        let repo = try RulesRepository.bundled()
                        loaded = (repo, SearchViewModel(repository: repo))
                    } catch {
                        loadError = error
                    }
                }
            }
        }
    }
}
