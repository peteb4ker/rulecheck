import SwiftUI

struct SearchView: View {
    @Bindable var model: SearchViewModel
    let repository: RulesRepository
    @AppStorage("searchScope") private var storedScope: String = SearchScope.all.rawValue
    @State private var path: [String] = []

    var body: some View {
        NavigationStack(path: $path) {
            List {
                if let message = model.errorMessage {
                    ErrorView(message: message)
                } else if model.query.trimmingCharacters(in: .whitespaces).isEmpty {
                    Section("Documents") {
                        ForEach(model.documents.filter { model.scope.docIds?.contains($0.id) ?? true }) { doc in
                            NavigationLink(value: doc) {
                                VStack(alignment: .leading) {
                                    Text(doc.title)
                                    Text("version \(doc.version) · \(doc.published)")
                                        .font(.caption).foregroundStyle(.secondary)
                                }
                            }
                        }
                    }
                } else if model.groups.isEmpty {
                    ContentUnavailableView.search(text: model.query)
                } else {
                    ForEach(model.groups, id: \.doc.id) { group in
                        Section(group.doc.title) {
                            ForEach(group.hits) { hit in
                                NavigationLink(value: hit.section.id) {
                                    VStack(alignment: .leading, spacing: 2) {
                                        Text(hit.section.breadcrumb)
                                            .font(.caption2).foregroundStyle(.secondary).lineLimit(1)
                                        Text(sectionRowTitle(hit.section)).font(.headline)
                                        Text(hit.snippet).font(.caption).foregroundStyle(.secondary).lineLimit(2)
                                    }
                                }
                            }
                        }
                    }
                }
            }
            .listStyle(.plain)
            .safeAreaInset(edge: .top) {
                Picker("Scope", selection: $model.scope) {
                    ForEach(SearchScope.allCases, id: \.self) { Text($0.label).tag($0) }
                }
                .pickerStyle(.segmented)
                .padding(.horizontal)
                .padding(.vertical, 6)
                .background(.bar)
            }
            .searchable(text: $model.query,
                        placement: .navigationBarDrawer(displayMode: .always),
                        prompt: "Search the rules")
            .navigationTitle("Benchwise")
            .toolbar {
                ToolbarItem(placement: .topBarTrailing) {
                    NavigationLink { AboutView(documents: model.documents) } label: {
                        Image(systemName: "info.circle")
                    }
                    .accessibilityLabel("About")
                    .accessibilityIdentifier("About")
                }
            }
            .navigationDestination(for: String.self) { id in
                SectionView(id: id, repository: repository, path: $path)
            }
            .navigationDestination(for: DocumentInfo.self) { doc in
                DocumentOutlineView(doc: doc, repository: repository)
            }
            .task(id: model.query) {
                try? await Task.sleep(for: .milliseconds(150))
                guard !Task.isCancelled else { return }
                model.refresh()
            }
            .onChange(of: model.scope) { _, newValue in
                storedScope = newValue.rawValue
                model.refresh()
            }
            .onAppear {
                model.scope = SearchScope(rawValue: storedScope) ?? .all
            }
        }
    }
}


func sectionRowTitle(_ section: RuleSection) -> String {
    if let n = section.citableNumber { return "\(n)  \(section.title)" }
    return section.title
}

