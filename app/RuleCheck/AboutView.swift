import SwiftUI

struct AboutView: View {
    let documents: [DocumentInfo]
    var body: some View {
        List {
            Section {
                ForEach(documents) { doc in
                    VStack(alignment: .leading, spacing: 3) {
                        Text(doc.title)
                            .font(.headline)
                            .foregroundStyle(Palette.ink)
                        (Text(doc.version) + Text(" · ") + Text(doc.published).monospaced())
                            .font(.caption)
                            .foregroundStyle(Palette.secondary)
                    }
                    .listRowBackground(Palette.surface)
                }
            } header: {
                Text("Documents").sectionLabelStyle()
            }
            Section {
                Group {
                    Text("Rule Check is an unofficial rules reference. It is not affiliated with, endorsed, sponsored, or specifically approved by The Pokémon Company International, Nintendo, Creatures, or GAME FREAK.")
                    Text("Rule Check makes zero network calls. Everything works offline; nothing is tracked.")
                    Text("Built with GRDB.swift (MIT License).")
                    // CC BY 3.0 requires attribution wherever the mark ships.
                    // The link is rendered, not fetched — the app still makes
                    // zero network calls; tapping it hands off to Safari.
                    Text("App icon: whistle by ProSymbols from Noun Project, [CC BY 3.0](https://thenounproject.com/browse/icons/term/whistle/).")
                }
                .font(.footnote)
                .foregroundStyle(Palette.body)
                .listRowBackground(Palette.surface)
            } header: {
                Text("About").sectionLabelStyle()
            }
        }
        .scrollContentBackground(.hidden)
        .background(Palette.canvas)
        .navigationTitle("About")
    }
}
