package content

import (
	"path/filepath"
	"testing"
)

func TestBooksCarryCatalogSeedTranslator(t *testing.T) {
	service := New(filepath.Join("..", "..", "..", "..", "content"))
	books, err := service.Books()
	if err != nil {
		t.Fatal(err)
	}

	bySlug := make(map[string]Book, len(books))
	for _, book := range books {
		bySlug[book.Slug] = book
	}

	daXue := bySlug["da-xue"]
	if daXue.SeedTranslator == nil || daXue.SeedTranslator.Translator != "Legge" {
		t.Fatalf("da-xue seed translator = %#v, want Legge", daXue.SeedTranslator)
	}
	sanguo := bySlug["sanguo-yanyi"]
	if sanguo.SeedTranslator == nil || sanguo.SeedTranslator.Translator != "C. H. Brewitt-Taylor" {
		t.Fatalf("sanguo seed translator = %#v, want C. H. Brewitt-Taylor", sanguo.SeedTranslator)
	}
}
