package dev.findfirst.bookmarkit.model;

import com.fasterxml.jackson.annotation.JsonIgnore;
import jakarta.persistence.CascadeType;
import jakarta.persistence.Column;
import jakarta.persistence.Entity;
import jakarta.persistence.FetchType;
import jakarta.persistence.GeneratedValue;
import jakarta.persistence.GenerationType;
import jakarta.persistence.Id;
import jakarta.persistence.ManyToMany;
import jakarta.persistence.Table;
import java.util.Set;
import lombok.AllArgsConstructor;
import lombok.Getter;
import lombok.NonNull;
import lombok.Setter;

@Entity
@Table(name = "tag")
@Getter
@Setter
@AllArgsConstructor
public class Tag {
  @Id
  @GeneratedValue(strategy = GenerationType.IDENTITY)
  private long id;

  @Column(name = "tag_title")
  @NonNull private String title;

  @ManyToMany(
      fetch = FetchType.EAGER,
      cascade = {CascadeType.ALL},
      mappedBy = "tags")
  @JsonIgnore
  Set<Bookmark> bookmarks;

  public Tag(String tagVal) {
    this.title = tagVal;
  }

  public Set<Bookmark> getBookmarks() {
    return this.bookmarks;
  }

  public Tag() {}

  @Override
  public boolean equals(Object obj) {
    if (obj instanceof Tag) {
      Tag t = (Tag) obj;
      return t.title.equals(this.title);
    } else return false;
  }

  @Override
  public int hashCode() {
    return title.hashCode();
  }
}