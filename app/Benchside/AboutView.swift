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
                    Text("Benchwise is an unofficial rules reference. It is not affiliated with, endorsed, sponsored, or specifically approved by The Pokémon Company International, Nintendo, Creatures, or GAME FREAK.")
                    Text("Benchwise makes zero network calls. Everything works offline; nothing is tracked.")
                    Text("Built with GRDB.swift (MIT License).")
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
