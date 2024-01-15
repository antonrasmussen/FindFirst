import { beforeAll, expect, it, test, vi } from "vitest";
import { render, screen } from "@testing-library/react";
import Page from "../app/page";
import { debug } from "vitest-preview";
import { beforeEach, describe } from "node:test";
import authService, { User } from "@services/auth.service";
import UseAuth from "@components/UseAuth";
import api, { instance } from "@api/Api";
import axios from "axios";
import MockAdapter from "axios-mock-adapter";
import Bookmark from "@type/Bookmarks/Bookmark";
import Tag from "@type/Bookmarks/Tag";

const myTags: Tag[] = [
  {
    id: 1,
    tag_title: "Cooking",
  },
  {
    id: 2,
    tag_title: "web_dev",
  },
  {
    id: 3,
    tag_title: "deserts",
  },
];
const bkmkResp: Bookmark[] = [
  {
    'id': 1,
    'title': "Best Cheesecake Recipe",
    'url': "https://sugarspunrun.com/best-cheesecake-recipe/",
    'tags': [myTags[0]]
  },
  {
    id: 2,
    title: "Dark mode guide",
    url: "https://blog.logrocket.com/dark-mode-react-in-depth-guide/",
    tags: [myTags[1]],
  },
  {
    id: 3,
    title: "Chicken Parm",
    url: "https://www.foodnetwork.com/recipes/bobby-flay/chicken-parmigiana-recipe-1952359",
    tags: [myTags[0]],
  },
];
const data = JSON.stringify(bkmkResp, null, 2 );

describe("user not authenticated", () => {
  it("Page loads", () => {
    render(<Page />);
    expect(screen.getByText("Hello Welcome to findfirst.")).toBeDefined();
  });
});

describe("User is authenticated and bookmark/tag data is present.", () => {
  const user: User = { username: "jsmith", refreshToken: "blahblajhdfh34234" };

  test("should be bookmarks available", async () => {
    let MockAdapter = require("axios-mock-adapter");
    var mock = new MockAdapter(instance);
    // Mock GET request to /users when param `searchText` is 'John'
    // arguments for reply are (status, data, headers)
    mock.onGet("/bookmarks").reply(200, data);

    mock.onGet("/tags").reply(200, "[]");

    await api.getAllBookmarks();

    console.log("after calls");
    vi.spyOn(authService, "getUser").mockImplementation(() => user);
    vi.spyOn(authService, "getAuthorized").mockImplementation(() => 1);
    render(<Page />);
    debug();
  });
});
