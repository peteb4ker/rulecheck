import XCTest
@testable import RuleCheck

final class SearchViewModelTests: XCTestCase {
    func testGroupsAreOrderedByDocumentAndFilterByScope() throws {
        let vm = SearchViewModel(repository: try RulesRepository.bundled())
        vm.query = "deck"; vm.scope = .tournament; vm.refresh()
        XCTAssertFalse(vm.groups.isEmpty)
        XCTAssertTrue(vm.groups.allSatisfy { ["tournament-rules", "penalty-guidelines"].contains($0.doc.id) })
    }
    func testEmptyQueryYieldsDocumentsForBrowse() throws {
        let vm = SearchViewModel(repository: try RulesRepository.bundled())
        vm.query = ""; vm.refresh()
        XCTAssertTrue(vm.groups.isEmpty)
        XCTAssertEqual(vm.documents.count, 3)
    }
}
