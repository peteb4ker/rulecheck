import SwiftUI

struct AboutView: View {
    let documents: [DocumentInfo]
    var body: some View {
        List {
            Section("Documents") {
                ForEach(documents) { doc in
                    VStack(alignment: .leading) {
                        Text(doc.title)
                        Text("version \(doc.version) · published \(doc.published)")
                            .font(.caption).foregroundStyle(.secondary)
                    }
                }
            }
            Section("About") {
                Text("Benchwise is an unofficial rules reference. It is not affiliated with, endorsed, sponsored, or specifically approved by The Pokémon Company International, Nintendo, Creatures, or GAME FREAK.")
                    .font(.footnote)
                Text("Benchwise makes zero network calls. Everything works offline; nothing is tracked.")
                    .font(.footnote)
                Text("Built with GRDB.swift (MIT License).")
                    .font(.footnote)
            }
        }
        .navigationTitle("About")
    }
}
