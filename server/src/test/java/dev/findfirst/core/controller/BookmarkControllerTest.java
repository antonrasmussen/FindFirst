package dev.findfirst.core.controller;

import static dev.findfirst.utilities.HttpUtility.getHttpEntity;
import static org.junit.Assert.assertFalse;
import static org.junit.jupiter.api.Assertions.assertEquals;
import static org.junit.jupiter.api.Assertions.assertTrue;

import dev.findfirst.core.annotations.IntegrationTest;
import dev.findfirst.core.model.AddBkmkReq;
import dev.findfirst.core.model.Bookmark;
import dev.findfirst.core.model.BookmarkTagPair;
import dev.findfirst.core.model.Tag;
import dev.findfirst.core.repository.BookmarkRepository;
import java.util.Arrays;
import java.util.List;
import java.util.Optional;
import org.junit.jupiter.api.Test;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.boot.test.context.SpringBootTest;
import org.springframework.boot.test.web.client.TestRestTemplate;
import org.springframework.boot.testcontainers.service.connection.ServiceConnection;
import org.springframework.http.HttpEntity;
import org.springframework.http.HttpMethod;
import org.springframework.http.HttpStatus;
import org.testcontainers.containers.PostgreSQLContainer;
import org.testcontainers.junit.jupiter.Container;
import org.testcontainers.junit.jupiter.Testcontainers;

@Testcontainers
@IntegrationTest
@SpringBootTest(webEnvironment = SpringBootTest.WebEnvironment.RANDOM_PORT)
public class BookmarkControllerTest {

  @Container @ServiceConnection
  static PostgreSQLContainer<?> postgres = new PostgreSQLContainer<>("postgres:16.2-alpine3.19");

  @Autowired BookmarkRepository bkmkRepo;

  @Autowired TestRestTemplate restTemplate;
  private String baseUrl = "/api/bookmarks";

  @Test
  void containerStarupTest() {
    assertEquals(postgres.isRunning(), true);
  }

  @Test
  void shouldFailBecauseNoOneIsAuthenticated() {
    var response = restTemplate.getForEntity(baseUrl, Bookmark.class);
    assertEquals(HttpStatus.UNAUTHORIZED, response.getStatusCode());
  }

  @Test
  void shouldPassIsAuthenticated() {
    var response =
        restTemplate.exchange(
            baseUrl, HttpMethod.GET, getHttpEntity(restTemplate), Bookmark[].class);
    assertEquals(HttpStatus.OK, response.getStatusCode());
  }

  @Test
  void getBookmarkById() {
    var response =
        restTemplate.exchange(
            "/api/bookmark?id=1", HttpMethod.GET, getHttpEntity(restTemplate), Bookmark.class);
    assertEquals(HttpStatus.OK, response.getStatusCode());

    var bkmkOpt = Optional.ofNullable(response.getBody());
    var bkmk = bkmkOpt.orElseThrow();
    assertEquals("Best Cheesecake Recipe", bkmk.getTitle());
  }

  @Test
  void addBookmark() {
    var ent = getHttpEntity(restTemplate, new AddBkmkReq("Facebook", "facebook.com", List.of()));
    var response = restTemplate.exchange("/api/bookmark", HttpMethod.POST, ent, Bookmark.class);
    assertEquals(HttpStatus.OK, response.getStatusCode());
    var bkmk = Optional.ofNullable(response.getBody());
    assertEquals("Facebook", bkmk.orElseThrow().getTitle());
  }

  @Test
  void addAllBookmarks() {
    saveBookmarks(
        new AddBkmkReq("Test", "Test.com", List.of()),
        new AddBkmkReq("Integration test", "IntegrationTesting.com", List.of()));
  }

  @Test
  // should test that all of JSmith's bookmarks are deleted but no one else's
  // were removed.
  void deleteAllBookmarks() {
    var response =
        restTemplate.exchange(
            baseUrl, HttpMethod.DELETE, getHttpEntity(restTemplate), String.class);
    assertEquals(HttpStatus.OK, response.getStatusCode());
    assertTrue(bkmkRepo.count() > 0);

    var bkmks =
        restTemplate.exchange(
            baseUrl, HttpMethod.GET, getHttpEntity(restTemplate), Bookmark[].class);

    assertEquals(HttpStatus.OK, response.getStatusCode());

    var bkmkOpt = Optional.ofNullable(bkmks.getBody());

    assertEquals(0, bkmkOpt.orElseThrow().length);
  }

  @Test
  void deleteTagFromBookmarkByTagTitle() {
    var bkmkResp =
        saveBookmarks(new AddBkmkReq("Web Color Picker", "htmlcolorcodes.com", List.of()));
    var bkmk = bkmkResp.get(0);

    // Add web_dev to bookmark
    var ent = getHttpEntity(restTemplate);
    restTemplate.exchange(
        "/api/bookmark/{bookmarkID}/tag?tag={title}",
        HttpMethod.POST,
        ent,
        Tag.class,
        bkmk.getId(),
        "web_dev");

    // Add design tag to bookmark.
    ent = getHttpEntity(restTemplate);
    restTemplate.exchange(
        "/api/bookmark/{bookmarkID}/tag?tag={title}",
        HttpMethod.POST,
        ent,
        Tag.class,
        bkmk.getId(),
        "design");

    // Delete first tag.
    restTemplate.exchange(
        "/api/bookmark/{bookmarkID}/tag?tag={tagName}",
        HttpMethod.DELETE,
        getHttpEntity(restTemplate),
        Tag.class,
        bkmk.getId(),
        "web_dev");

    var response =
        restTemplate.exchange(
            "/api/bookmark?id={id}",
            HttpMethod.GET,
            getHttpEntity(restTemplate),
            Bookmark.class,
            bkmk.getId());
    assertEquals(HttpStatus.OK, response.getStatusCode());

    var bkmkOpt = Optional.ofNullable(response.getBody());
    bkmk = bkmkOpt.orElseThrow();
    assertEquals(1, bkmk.getTags().size());
    assertFalse(bkmk.getTags().stream().anyMatch(t -> t.getTag_title().equals("web_dev")));
  }

  @Test
  void deleteTagFromBookmarkById() {
    var bkmkResp = saveBookmarks(new AddBkmkReq("Color Picker2", "htmlcolorcodes2.com", List.of()));
    var bkmk = bkmkResp.get(0);

    // Add Tag web_dev
    var ent = getHttpEntity(restTemplate);
    restTemplate.exchange(
        "/api/bookmark/{bookmarkID}/tag?tag={title}",
        HttpMethod.POST,
        ent,
        Tag.class,
        bkmk.getId(),
        "web_dev");

    // Add Tag design
    // Store tag response to delete the tag next
    ent = getHttpEntity(restTemplate);
    var tagOpt =
        Optional.ofNullable(
            restTemplate
                .exchange(
                    "/api/bookmark/{bookmarkID}/tag?tag={title}",
                    HttpMethod.POST,
                    ent,
                    Tag.class,
                    bkmk.getId(),
                    "design")
                .getBody());
    long tagId = tagOpt.orElseThrow().getId();

    // Delete by the id.
    restTemplate.exchange(
        "/api/bookmark/{bookmarkID}/tagId?tagId={id}",
        HttpMethod.DELETE,
        getHttpEntity(restTemplate),
        Tag.class,
        bkmk.getId(),
        tagId);

    // See that one tag remains on the bookmark
    var response =
        restTemplate.exchange(
            "/api/bookmark?id={id}",
            HttpMethod.GET,
            getHttpEntity(restTemplate),
            Bookmark.class,
            bkmk.getId());
    assertEquals(HttpStatus.OK, response.getStatusCode());

    var bkmkOpt = Optional.ofNullable(response.getBody());
    bkmk = bkmkOpt.orElseThrow();
    assertFalse(bkmk.getTags().stream().anyMatch(t -> t.getId() == tagId));
  }

  @Test
  void addTagToBookmarkById() {
    var bkmk =
        saveBookmarks(new AddBkmkReq("Spring Docs 3.2", "Spring.io/docs/3.2", List.of((long) 1)));
    var tagReq =
        restTemplate.exchange(
            "/api/bookmark/{bookmarkID}/tagId?tagId={id}",
            HttpMethod.POST,
            getHttpEntity(restTemplate),
            BookmarkTagPair.class,
            bkmk.get(0).getId(),
            5);
    var btPairOpt = Optional.ofNullable(tagReq.getBody());
    var tags = btPairOpt.orElseThrow().bkmk().getTags();

    assertTrue(tags.stream().filter(t -> t.getId() == 5 || t.getId() == 1).count() == 2);
  }

  @Test
  void deleteBookmarkById() {
    saveBookmarks(
        new AddBkmkReq(
            "color theory for designers",
            "https://webflow.com/blog/color-theory",
            List.of(1L, 6L)));
    var response =
        restTemplate.exchange(
            baseUrl, HttpMethod.GET, getHttpEntity(restTemplate), Bookmark[].class);
    var bkmkOpt = Optional.ofNullable(response.getBody());

    var id = bkmkOpt.orElseThrow()[0].getId();
    var delResp =
        restTemplate.exchange(
            "/api/bookmark?id={id}",
            HttpMethod.DELETE,
            getHttpEntity(restTemplate),
            String.class,
            id);
    assertEquals(HttpStatus.OK, delResp.getStatusCode());
  }

  private List<Bookmark> saveBookmarks(AddBkmkReq... newBkmks) {
    HttpEntity<?> ent;
    if (newBkmks.length == 1) {
      ent = getHttpEntity(restTemplate, newBkmks[0]);
      var bkmkResp = restTemplate.exchange("/api/bookmark", HttpMethod.POST, ent, Bookmark.class);
      return List.of(bkmkResp.getBody());
    }
    ent = getHttpEntity(restTemplate, Arrays.asList(newBkmks));
    var blResp =
        restTemplate.exchange("/api/bookmark/addBookmarks", HttpMethod.POST, ent, Bookmark[].class);
    assertEquals(HttpStatus.OK, blResp.getStatusCode());
    return List.of(blResp.getBody());
  }
}
