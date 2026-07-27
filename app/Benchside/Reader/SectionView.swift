import SwiftUI

struct SectionView: View {
    let id: String
    let repository: RulesRepository
    @Binding var path: [String]

    var body: some View {
        if let section = try? repository.section(id: id) {
            content(for: section)
        } else {
            ErrorView(message: "Section \(id) not found")
        }
    }

    @ViewBuilder
    private func content(for section: RuleSection) -> some View {
        let refs = (try? repository.crossReferences(from: section.id)) ?? []
        let neighbors = (try? repository.neighbors(of: section)) ?? (prev: nil, next: nil)
        let doc = try? repository.documentInfo(id: section.docId)

        ScrollView {
            VStack(alignment: .leading, spacing: 12) {
                Text(section.breadcrumb)
                    .font(.caption).foregroundStyle(.secondary)
                Text(sectionRowTitle(section))
                    .font(.title2.bold())
                Text(section.body)
                    .font(.body)
                    .textSelection(.enabled)
                if !refs.isEmpty {
                    Divider()
                    Text("See also").font(.caption).foregroundStyle(.secondary)
                    ForEach(refs) { ref in
                        Button(sectionRowTitle(ref)) { path.append(ref.id) }
                            .font(.subheadline)
                    }
                }
                if let doc {
                    Divider()
                    Text("\(doc.title) — version \(doc.version), \(doc.published)")
                        .font(.caption2).foregroundStyle(.secondary)
                }
            }
            .padding()
        }
        .navigationBarTitleDisplayMode(.inline)
        .toolbar {
            ToolbarItemGroup(placement: .bottomBar) {
                Button { if let p = neighbors.prev { path[path.count - 1] = p.id } } label: {
                    Label("Previous", systemImage: "chevron.up")
                }.disabled(neighbors.prev == nil)
                Spacer()
                Button { if let n = neighbors.next { path[path.count - 1] = n.id } } label: {
                    Label("Next", systemImage: "chevron.down")
                }.disabled(neighbors.next == nil)
            }
        }
    }
}
